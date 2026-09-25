"""
AUTOSAR HLD AI - Unified Application Launcher
Allows launching the FastAPI Backend, Streamlit Dashboard, or both.
"""

import os
import sys
import subprocess
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def run_backend(host: str = "0.0.0.0", port: int = 8000):
    """Run FastAPI backend server using uvicorn."""
    import uvicorn
    print(f"🚀 Starting AUTOSAR HLD AI FastAPI Server on http://{host}:{port}")
    uvicorn.run("app.backend.main:app", host=host, port=port, reload=True)


def run_frontend(port: int = 8501):
    """Run Streamlit engineering frontend dashboard."""
    streamlit_app_path = os.path.join(BASE_DIR, "app", "frontend", "streamlit_app.py")
    print(f"🚀 Starting Streamlit Dashboard on http://localhost:{port}")
    cmd = [sys.executable, "-m", "streamlit", "run", streamlit_app_path, "--server.port", str(port)]
    subprocess.run(cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUTOSAR HLD AI Assistant Launcher")
    parser.add_argument("--mode", choices=["frontend", "backend", "all"], default="frontend", help="Mode to launch")
    parser.add_argument("--port", type=int, default=8501, help="Port number")
    args = parser.parse_args()

    if args.mode == "backend":
        run_backend(port=args.port)
    elif args.mode == "frontend":
        run_frontend(port=args.port)
    else:
        print("To run both concurrently in separate terminals:")
        print("Terminal 1: python run.py --mode backend --port 8000")
        print("Terminal 2: python run.py --mode frontend --port 8501")
        run_frontend(port=8501)
