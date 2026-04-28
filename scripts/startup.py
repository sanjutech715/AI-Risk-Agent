"""
scripts/startup.py
───────────────────
Automated startup & smoke-test script.
  1. Kills any stale process on port 8000
  2. Starts the FastAPI server (via uv or python)
  3. Waits until /health responds 200
  4. Runs smoke tests on /health and /api/v1/analyze
  5. Saves outputs to data/

Usage:
    uv run python scripts/startup.py
    python scripts/startup.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "http://127.0.0.1:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────

def cleanup_port(port: int = 8000):
    print(f"🧹 Freeing port {port}...")
    if sys.platform == "win32":
        subprocess.run(
            ["powershell", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue "
             f"| ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True, timeout=5,
        )
    else:
        subprocess.run(f"fuser -k {port}/tcp 2>/dev/null || true", shell=True)
    time.sleep(0.5)


def start_server() -> subprocess.Popen:
    print("🚀 Starting FastAPI server...")
    cmd = ["python", str(ROOT / "app.py")]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )


def wait_for_server(max_tries: int = 20) -> bool:
    for _ in range(max_tries):
        try:
            if requests.get(f"{BASE}/health", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ── Smoke tests ───────────────────────────────────────────────────────────────

def test_health() -> bool:
    print("🏥 Testing /health ...")
    r = requests.get(f"{BASE}/health", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print("✅ Health OK:", json.dumps(data, indent=2))
        (DATA_DIR / "health_check_output.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        return True
    print(f"❌ Health returned {r.status_code}")
    return False


def test_analyze() -> bool:
    print("📊 Testing /api/v1/analyze ...")
    payload = {
        "document_id": "TEST001",
        "standardized_data": {
            "document_type": "invoice",
            "issuer": "Test Company",
            "amount": 50000.00,
            "currency": "USD",
            "issue_date": "2026-04-18",
            "counterparty": "Client XYZ",
            "jurisdiction": "US",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": True,
            "missing_fields": [],
            "anomalies": [],
            "schema_errors": [],
            "completeness_score": 0.95,
        },
    }
    r = requests.post(f"{BASE}/api/v1/analyze", json=payload, timeout=30)
    if r.status_code == 200:
        data = r.json()
        print("✅ Analyze OK:", json.dumps(data, indent=2))
        (DATA_DIR / "analyze_endpoint_output.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        return True
    print(f"❌ Analyze returned {r.status_code}: {r.text}")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("   RISK AGENT API — AUTOMATED STARTUP & TEST")
    print("=" * 60)

    cleanup_port()
    proc = start_server()

    print("⏳ Waiting for server...")
    if not wait_for_server():
        print("❌ Server failed to start!")
        proc.terminate()
        sys.exit(1)

    print("✅ Server ready!\n")

    try:
        ok = test_health() and test_analyze()
        if ok:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED!")
            print(f"   API  → {BASE}")
            print(f"   Docs → {BASE}/docs")
            print("=" * 60)
        else:
            print("❌ Some tests failed.")
            sys.exit(1)
    finally:
        print("\n🛑 Shutting down...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("✅ Done.")


if __name__ == "__main__":
    main()
