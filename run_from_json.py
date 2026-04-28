"""
run_from_json.py
─────────────────
Send a single document from data/risk_agent.json to the running API
and save the response to data/risk_agent_output.json.

Usage:
    python run_from_json.py
    uv run python run_from_json.py
"""

import json
import sys
from pathlib import Path

import httpx

BASE_URL   = "http://127.0.0.1:8000"
INPUT_FILE = Path(__file__).parent / "data" / "risk_agent.json"
OUTPUT_FILE = Path(__file__).parent / "data" / "risk_agent_output.json"


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"❌ Missing input file: {INPUT_FILE}")
        return 1

    try:
        payload = json.loads(INPUT_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        print(f"❌ Invalid JSON in {INPUT_FILE}: {exc}")
        return 1

    url = f"{BASE_URL}/api/v1/analyze"
    print(f"📤 Sending {INPUT_FILE.name} → {url}")

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"❌ Connection error: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        print(f"❌ API error {exc.response.status_code}: {exc.response.text}")
        return 1

    output = response.json()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(output, indent=2))
    print(f"\n💾 Response saved to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
