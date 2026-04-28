#!/usr/bin/env python
"""
Risk Agent API — Entry Point
Run with:  python app.py
       or: uv run python app.py
"""

import uvicorn
import os


def main():
    uvicorn.run(
        "app_module.main:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("UVICORN_RELOAD", "0") == "1",
        log_level="info",
    )



if __name__ == "__main__":
    main()
