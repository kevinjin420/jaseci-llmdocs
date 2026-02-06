#!/usr/bin/env python3
import asyncio
import re
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .runner import PipelineRunner
from ..pipeline.sources import SourceManager, Source, SourceType
from ..pipeline.validator import Validator
from ..pipeline.docs_validator import OfficialDocsValidator


class SourceCreate(BaseModel):
    id: str
    git_url: str
    branch: str = "main"
    path: str = "."
    source_type: str = "docs"
    enabled: bool = True
    file_patterns: list[str] = None


class SourceUpdate(BaseModel):
    git_url: str = None
    branch: str = None
    path: str = None
    source_type: str = None
    enabled: bool = None
    file_patterns: list[str] = None


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
source_manager: Optional[SourceManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner, source_manager
    config_path = Path(__file__).parents[2] / "config" / "config.yaml"
    runner = PipelineRunner(config_path, manager.broadcast)
    source_manager = SourceManager(config_path)
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


@app.post("/api/run/{stage}")
async def run_stage(stage: str):
    valid_stages = ["fetch", "extract", "assemble"]
    if stage not in valid_stages:
        return {"error": f"Invalid stage. Must be one of: {valid_stages}"}
    if runner:
        if runner.is_running:
            return {"error": "Pipeline already running"}
        asyncio.create_task(runner.run_stage(stage))
        return {"status": "started", "stage": stage}
    return {"error": "Runner not initialized"}


@app.get("/api/stages")
async def get_stages():
    if runner:
        return runner.get_stage_details()
    return []


@app.get("/api/sources")
async def list_sources():
    if source_manager:
        return [s.to_dict() for s in source_manager.list()]
    return []


@app.get("/api/sources/{source_id}")
async def get_source(source_id: str):
    if source_manager:
        source = source_manager.get(source_id)
        if source:
            return source.to_dict()
        raise HTTPException(status_code=404, detail="Source not found")
    raise HTTPException(status_code=500, detail="Source manager not initialized")


@app.post("/api/sources")
async def create_source(data: SourceCreate):
    if not source_manager:
        raise HTTPException(status_code=500, detail="Source manager not initialized")

    try:
        file_patterns = ','.join(data.file_patterns) if data.file_patterns else None
        source = Source(
            id=data.id,
            git_url=data.git_url,
            branch=data.branch,
            path=data.path,
            source_type=SourceType(data.source_type),
            enabled=data.enabled,
            file_patterns=file_patterns
        )
        result = source_manager.add(source)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/sources/{source_id}")
async def update_source(source_id: str, data: SourceUpdate):
    if not source_manager:
        raise HTTPException(status_code=500, detail="Source manager not initialized")

    try:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        result = source_manager.update(source_id, updates)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: str):
    if not source_manager:
        raise HTTPException(status_code=500, detail="Source manager not initialized")

    try:
        source_manager.delete(source_id)
        return {"status": "deleted", "id": source_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/sources/{source_id}/toggle")
async def toggle_source(source_id: str):
    if not source_manager:
        raise HTTPException(status_code=500, detail="Source manager not initialized")

    source = source_manager.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    result = source_manager.update(source_id, {"enabled": not source.enabled})
    return result.to_dict()


# Config and Prompts API
CONFIG_DIR = Path(__file__).parents[2] / "config"

@app.get("/api/config")
async def get_config():
    config_path = CONFIG_DIR / "config.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    return {"content": config_path.read_text()}


@app.put("/api/config")
async def update_config(data: dict):
    config_path = CONFIG_DIR / "config.yaml"
    try:
        import yaml
        yaml.safe_load(data["content"])
        config_path.write_text(data["content"])
        return {"status": "saved"}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")


@app.get("/api/prompts")
async def list_prompts():
    prompts = []
    for f in CONFIG_DIR.glob("*_prompt.txt"):
        prompts.append({
            "name": f.stem,
            "filename": f.name
        })
    return prompts


@app.get("/api/prompts/{filename}")
async def get_prompt(filename: str):
    prompt_path = CONFIG_DIR / filename
    if not prompt_path.exists() or not filename.endswith("_prompt.txt"):
        raise HTTPException(status_code=404, detail="Prompt file not found")
    return {"filename": filename, "content": prompt_path.read_text()}


@app.put("/api/prompts/{filename}")
async def update_prompt(filename: str, data: dict):
    if not filename.endswith("_prompt.txt"):
        raise HTTPException(status_code=400, detail="Invalid prompt filename")
    prompt_path = CONFIG_DIR / filename
    prompt_path.write_text(data["content"])
    return {"status": "saved", "filename": filename}


ROOT = Path(__file__).parents[2]


@app.post("/api/validate")
async def validate_output():
    """Validate the current output against jac check and official docs."""
    output_path = ROOT / "output" / "2_final" / "jac_reference.txt"
    if not output_path.exists():
        release_path = ROOT.parent / "release" / "candidate.txt"
        if release_path.exists():
            output_path = release_path
        else:
            raise HTTPException(status_code=404, detail="No output to validate")

    text = output_path.read_text()

    validator = Validator()
    docs_validator = OfficialDocsValidator()

    jac_results = validator.validate_all_examples(text)

    syntax_verification = docs_validator.validate_syntax_in_output(text)
    syntax_results = {
        v.construct: {
            "expected": v.expected,
            "found": v.found_in_output,
            "correct": v.matches_docs
        }
        for v in syntax_verification
    }

    pattern_checks = {
        'spawn_correct': bool(
            re.search(r'\bspawn\s+\w+|\w+\s+spawn\b', text)
        ),
        'tuple_correct': '(a, b) =' in text or '(x, y) =' in text,
        'connect_correct': '+>:' in text and ':+>' in text,
        'by_llm_correct': 'by llm;' in text or 'by llm(' in text,
    }

    all_syntax_ok = all(v.matches_docs for v in syntax_verification if v.found_in_output)
    all_patterns_ok = all(pattern_checks.values())

    is_valid = jac_results.pass_rate >= 95 and all_syntax_ok and all_patterns_ok

    return {
        "source_file": str(output_path),
        "jac_check": {
            "total": jac_results.total_blocks,
            "passed": jac_results.passed,
            "failed": jac_results.failed,
            "skipped": jac_results.skipped,
            "pass_rate": jac_results.pass_rate,
            "errors": jac_results.errors[:10]
        },
        "syntax_verification": syntax_results,
        "pattern_checks": pattern_checks,
        "docs_summary": docs_validator.get_docs_summary(),
        "recommendation": "PASS" if is_valid else "REVIEW",
        "is_valid": is_valid
    }


@app.get("/api/validate/docs-info")
async def get_docs_info():
    """Get information about loaded official docs for debugging."""
    docs_validator = OfficialDocsValidator()
    return docs_validator.get_docs_summary()


@app.get("/api/candidate")
async def get_candidate():
    """Get the current candidate.txt content."""
    release_path = ROOT.parent / "release" / "candidate.txt"
    if not release_path.exists():
        raise HTTPException(status_code=404, detail="No candidate.txt found")
    return {"content": release_path.read_text()}
