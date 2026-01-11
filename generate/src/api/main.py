#!/usr/bin/env python3
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .runner import PipelineRunner


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.connections[:]:
            try:
                await ws.send_json(data)
            except:
                self.disconnect(ws)


manager = ConnectionManager()
runner: Optional[PipelineRunner] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    config_path = Path(__file__).parents[2] / "config" / "config.yaml"
    runner = PipelineRunner(config_path, manager.broadcast)
    yield


app = FastAPI(title="Pipeline Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/api/status")
async def get_status():
    if runner:
        return runner.get_status()
    return {"status": "not_initialized"}


@app.get("/api/metrics")
async def get_metrics():
    if runner:
        return runner.get_metrics()
    return {}


@app.post("/api/run")
async def run_pipeline():
    if runner:
        if runner.is_running:
            return {"error": "Pipeline already running"}
        asyncio.create_task(runner.run())
        return {"status": "started"}
    return {"error": "Runner not initialized"}


@app.get("/api/stages")
async def get_stages():
    if runner:
        return runner.get_stage_details()
    return []
