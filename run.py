"""Application entrypoint for the Risk Agent API."""

import os
import socket

from app.main import app


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


if __name__ == "__main__":
    import uvicorn

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