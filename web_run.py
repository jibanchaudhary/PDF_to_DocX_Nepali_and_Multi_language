from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
DIST = os.path.join(FRONTEND, "dist")


def ensure_frontend_built() -> None:
    """Build the Vite SPA into frontend/dist if it isn't there yet."""
    if os.path.isdir(DIST):
        return
    npm = shutil.which("npm")
    if npm is None:
        print(
            "✗ frontend/dist is missing and `npm` was not found.\n"
            "  Install Node 18+ and build it:\n"
            "    cd frontend && npm install && npm run build",
            file=sys.stderr,
        )
        sys.exit(1)
    print("→ building frontend (first run)…")
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        subprocess.run([npm, "install"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the PDFlow web app.")
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="bind port (default 8000)")
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes")
    parser.add_argument("--no-build", action="store_true",
                        help="don't build the frontend even if dist is missing")
    args = parser.parse_args(argv)

    os.chdir(ROOT)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    try:
        import uvicorn 
    except ImportError:
        print(
            "✗ uvicorn is not installed in this interpreter.\n"
            "  Use the project venv and install the web layer:\n"
            "    ../.pvenv/bin/pip install -r backend/requirements.txt\n"
            f"  then:  ../.pvenv/bin/python {os.path.basename(__file__)}",
            file=sys.stderr,
        )
        return 1

    if not args.no_build:
        ensure_frontend_built()

    print(f"→ serving PDFlow on http://{args.host}:{args.port}")
    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
