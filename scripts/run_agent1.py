"""
Demo launcher for Agent 1's API — like `uvicorn src.main:app`, but the
server also stops cleanly when you type "exit" + Enter (Ctrl+C works
too).

Run:  python scripts/run_agent1.py
"""

import sys
import threading
from pathlib import Path

import uvicorn

# Running as `python scripts/run_agent1.py` puts scripts/ on sys.path,
# not the project root — add the root so "src.main:app" imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def watch_stdin(server: uvicorn.Server) -> None:
    for line in sys.stdin:
        if line.strip().lower() == "exit":
            print("[agent1] exit requested, shutting down", flush=True)
            server.should_exit = True
            return


if __name__ == "__main__":
    config = uvicorn.Config("src.main:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    print("[agent1] starting on http://localhost:8000 — type 'exit' to stop", flush=True)
    threading.Thread(target=watch_stdin, args=(server,), daemon=True).start()
    server.run()
