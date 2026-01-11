#!/usr/bin/env python3
"""
Start script for Pipeline Dashboard.
Fetches latest docs, then runs FastAPI backend and Vite dev server.
"""
import subprocess
import sys
import os
import signal
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"
JASECI_REPO = "https://github.com/jaseci-labs/jaseci.git"
DOCS_PATH = "docs/docs"


def fetch_docs():
    """Fetch latest docs from Jaseci repo using sparse checkout."""
    print("Fetching latest documentation...")

    if DOCS_DIR.exists():
        print("  Updating existing docs...")
        result = subprocess.run(
            ["git", "pull", "--depth=1"],
            cwd=DOCS_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  Docs updated.")
            return True
        else:
            print("  Pull failed, re-cloning...")
            shutil.rmtree(DOCS_DIR)

    print(f"  Cloning {DOCS_PATH} from {JASECI_REPO}...")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=DOCS_DIR, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", JASECI_REPO], cwd=DOCS_DIR, capture_output=True)
    subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=DOCS_DIR, capture_output=True)

    sparse_file = DOCS_DIR / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    sparse_file.write_text(f"{DOCS_PATH}/*\n")

    result = subprocess.run(
        ["git", "pull", "--depth=1", "origin", "main"],
        cwd=DOCS_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("  Docs fetched successfully.")
        return True
    else:
        print(f"  Error fetching docs: {result.stderr}")
        return False


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
    fetch_docs()
    check_dependencies()

    processes = []

    def cleanup(sig=None, frame=None):
        print("\nShutting down...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    print("Starting backend on http://localhost:4000")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "4000", "--reload"],
        cwd=ROOT,
        env=env
    )
    processes.append(backend)

    time.sleep(2)

    print("Starting frontend on http://localhost:4444")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "dashboard"
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
