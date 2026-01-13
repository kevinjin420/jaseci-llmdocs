#!/usr/bin/env python3
"""
Start script for Pipeline Dashboard.
Runs FastAPI backend and Vite dev server.
"""
import subprocess
import sys
import os
import signal
import time
from pathlib import Path

ROOT = Path(__file__).parent


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("Installing Python dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT)

    dashboard = ROOT / "dashboard"
    if not (dashboard / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=dashboard)


def main():
    check_dependencies()

    processes = []
    shutting_down = False

    def cleanup(sig=None, frame=None):
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\nShutting down...")
        for p in processes:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        time.sleep(0.5)
        for p in processes:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    print("Starting backend on http://localhost:4000")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "4000", "--reload"],
        cwd=ROOT,
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
        start_new_session=True
    )
    processes.append(backend)

    time.sleep(2)

    print("Starting frontend on http://localhost:4444")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "dashboard",
        stdout=sys.stdout,
        stderr=sys.stderr,
        start_new_session=True
    )
    processes.append(frontend)

    print("\n" + "=" * 50)
    print("Pipeline Dashboard")
    print("=" * 50)
    print("Frontend: http://localhost:4444")
    print("Backend:  http://localhost:4000")
    print("API Docs: http://localhost:4000/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            if backend.poll() is not None:
                print("Backend stopped unexpectedly")
                cleanup()
            if frontend.poll() is not None:
                print("Frontend stopped unexpectedly")
                cleanup()
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
