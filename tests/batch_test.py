"""
tests/batch_test.py
────────────────────
Sends 3 sample documents to the /api/v1/batch endpoint and prints results.

Usage:
    uv run python tests/batch_test.py
    python tests/batch_test.py
"""

import asyncio
import json

import httpx

BASE = "http://127.0.0.1:8000"

DOCS = [
    {
        "document_id": "BATCH001",
        "standardized_data": {
            "document_type": "invoice",
            "issuer": "Acme Corp",
            "amount": 15000.0,
            "currency": "USD",
            "issue_date": "2024-01-15",
            "expiry_date": "2024-04-15",
            "counterparty": "Globex Ltd",
            "jurisdiction": "US",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": True,
            "missing_fields": [],
            "anomalies": [],
            "schema_errors": [],
            "completeness_score": 0.97,
        },
    },
    {
        "document_id": "BATCH002",
        "standardized_data": {
            "document_type": "contract",
            "issuer": "Unknown Vendor",
            "amount": 450000.0,
            "currency": "EUR",
            "issue_date": "2024-01-10",
            "counterparty": None,
            "jurisdiction": "UK",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": False,
            "missing_fields": ["counterparty", "expiry_date"],
            "anomalies": ["amount exceeds threshold"],
            "schema_errors": [],
            "completeness_score": 0.65,
        },
    },
    {
        "document_id": "BATCH003",
        "standardized_data": {
            "document_type": "purchase_order",
            "issuer": None,
            "amount": 2500000.0,
            "currency": "USD",
            "issue_date": None,
            "expiry_date": None,
            "counterparty": None,
            "jurisdiction": None,
            "metadata": {},
        },
        "validation_result": {
            "is_valid": False,
            "missing_fields": ["issuer", "counterparty", "issue_date"],
            "anomalies": ["duplicate signature", "amount mismatch"],
            "schema_errors": ["missing required field: issuer"],
            "completeness_score": 0.22,
        },
    },
]


async def run_batch():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"📤 Sending {len(DOCS)} documents to {BASE}/api/v1/batch ...\n")
        resp = await client.post(f"{BASE}/api/v1/batch", json=DOCS)
        resp.raise_for_status()
        results = resp.json()

    print("─" * 55)
    for r in results:
        emoji = {"approve": "✅", "review": "⚠️", "reject": "❌"}.get(r["recommendation"], "?")
        print(
            f"{emoji} {r['document_id']:10s} | "
            f"rec={r['recommendation']:7s} | "
            f"score={r['risk_score']:.4f} | "
            f"conf={r['confidence']:.4f}"
        )
    print("─" * 55)
    print(f"\nFull response:\n{json.dumps(results, indent=2)}")


if __name__ == "__main__":
    asyncio.run(run_batch())
