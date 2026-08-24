#!/usr/bin/env python
"""DAP Startup Script - Launches the DevOps Agentic Platform.

Usage:
  python start_dap.py          # Start on default port (8000)
  python start_dap.py --port 9000  # Start on custom port

Requires: uvicorn, fastapi
"""

# ─── Add project root to Python path ──────────────────────────────
import sys
import os

# Resolve the project root from the absolute path of THIS script.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# The src/ directory contains main.py and all sub-packages.
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

# Ensure both project root and src/ are in sys.path.
for path in [PROJECT_ROOT, SRC_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import argparse


def main():
    parser = argparse.ArgumentParser(description="Start the DevOps Agentic Platform")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    print("Starting DAP on {}:{}".format(args.host, args.port))
    print("   API docs: http://localhost:{}/docs".format(args.port))
    print("   Metrics:  http://localhost:{}/api/observability/metrics".format(args.port))
    print("   IDE WS:   ws://localhost:{}/ws/<session_id>".format(args.port))
    print()

    # Import uvicorn and start the app — use direct module import
    import uvicorn

    from src.main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,  # Disable auto-reload in production-like mode,
    )


if __name__ == "__main__":
    main()
