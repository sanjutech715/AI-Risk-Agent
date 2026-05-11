"""Application entrypoint for the Risk Agent API."""

import os
import socket
import sys
from pathlib import Path


def _find_free_port(start_port: int, max_port: int = 8100) -> int:
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found between {start_port} and {max_port}")


def _ensure_project_virtualenv() -> None:
    project_root = Path(__file__).resolve().parent
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()

    if ".venv" in [part.lower() for part in current_python.parts]:
        return
    if not venv_python.exists():
        return
    if venv_python.resolve() == current_python:
        return

    print("NOTICE: Re-launching with the project virtual environment at .\.venv\Scripts\python.exe")
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)


def load_app():
    try:
        from app.main import app
        return app
    except ModuleNotFoundError as exc:
        if exc.name == "jose":
            print("ERROR: Could not import 'jose'. This usually means the active Python interpreter is not using the project's virtual environment.")
            print("Activate the venv and run the app with: .\\.venv\\Scripts\\activate && python run.py")
            print("Or start with the bundled Windows launcher: .\\run.bat")
        else:
            print(f"ERROR: Failed to import application module: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Failed to import application module: {exc}")
        sys.exit(1)


if __name__ != "__main__":
    app = load_app()


if __name__ == "__main__":
    import uvicorn

    _ensure_project_virtualenv()
    app = load_app()

    host = os.getenv("HOST", "127.0.0.1")
    desired_port = int(os.getenv("PORT", "8000"))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, desired_port))
        port = desired_port
    except OSError:
        port = _find_free_port(desired_port + 1)
        print(f"Port {desired_port} is in use; starting on port {port} instead.")

    uvicorn.run(app, host=host, port=port)