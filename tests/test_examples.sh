#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Decision, Summary & Risk Agent — Quick curl Tests
# Usage:  bash tests/test_examples.sh
# ──────────────────────────────────────────────────────────────────────────────

BASE="http://localhost:8000"

echo ""
echo "═══════════════════════════════════════════════"
echo "  1. HEALTH CHECK"
echo "═══════════════════════════════════════════════"
curl -s "$BASE/health" | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════════"
echo "  2. SINGLE DOCUMENT — approve (clean invoice)"
echo "═══════════════════════════════════════════════"
curl -s -X POST "$BASE/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "DOC001",
    "standardized_data": {
      "document_type": "invoice",
      "issuer": "Acme Corp",
      "amount": 15000.00,
      "currency": "USD",
      "issue_date": "2024-01-15",
      "expiry_date": "2024-04-15",
      "counterparty": "Globex Ltd",
      "jurisdiction": "US",
      "metadata": {}
    },
    "validation_result": {
      "is_valid": true,
      "missing_fields": [],
      "anomalies": [],
      "schema_errors": [],
      "completeness_score": 0.97
    }
  }' | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════════"
echo "  3. SINGLE DOCUMENT — review (missing fields)"
echo "═══════════════════════════════════════════════"
curl -s -X POST "$BASE/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "DOC002",
    "standardized_data": {
      "document_type": "contract",
      "issuer": "Unknown Vendor",
      "amount": 450000.00,
      "currency": "EUR",
      "issue_date": "2024-01-10",
      "counterparty": null,
      "jurisdiction": "UK",
      "metadata": {}
    },
    "validation_result": {
      "is_valid": false,
      "missing_fields": ["counterparty", "expiry_date"],
      "anomalies": ["amount exceeds threshold"],
      "schema_errors": [],
      "completeness_score": 0.65
    }
  }' | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════════"
echo "  4. SINGLE DOCUMENT — reject (high risk)"
echo "═══════════════════════════════════════════════"
curl -s -X POST "$BASE/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "DOC003",
    "standardized_data": {
      "document_type": "purchase_order",
      "issuer": null,
      "amount": 2500000.00,
      "currency": "USD",
      "issue_date": null,
      "expiry_date": null,
      "counterparty": null,
      "jurisdiction": null,
      "metadata": {}
    },
    "validation_result": {
      "is_valid": false,
      "missing_fields": ["issuer", "counterparty", "issue_date"],
      "anomalies": ["duplicate signature", "amount mismatch"],
      "schema_errors": ["missing required field: issuer"],
      "completeness_score": 0.22
    }
  }' | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════════"
echo "  5. BATCH TEST — 3 documents at once"
echo "═══════════════════════════════════════════════"
curl -s -X POST "$BASE/api/v1/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "document_id": "BATCH001",
      "standardized_data": {
        "document_type": "invoice", "issuer": "Acme Corp",
        "amount": 15000.00, "currency": "USD",
        "issue_date": "2024-01-15", "expiry_date": "2024-04-15",
        "counterparty": "Globex Ltd", "jurisdiction": "US", "metadata": {}
      },
      "validation_result": {
        "is_valid": true, "missing_fields": [], "anomalies": [],
        "schema_errors": [], "completeness_score": 0.97
      }
    },
    {
      "document_id": "BATCH002",
      "standardized_data": {
        "document_type": "contract", "issuer": "Unknown Vendor",
        "amount": 450000.00, "currency": "EUR",
        "issue_date": "2024-01-10", "counterparty": null,
        "jurisdiction": "UK", "metadata": {}
      },
      "validation_result": {
        "is_valid": false, "missing_fields": ["counterparty","expiry_date"],
        "anomalies": ["amount exceeds threshold"], "schema_errors": [],
        "completeness_score": 0.65
      }
    },
    {
      "document_id": "BATCH003",
      "standardized_data": {
        "document_type": "purchase_order", "issuer": null,
        "amount": 2500000.00, "currency": "USD",
        "issue_date": null, "expiry_date": null,
        "counterparty": null, "jurisdiction": null, "metadata": {}
      },
      "validation_result": {
        "is_valid": false, "missing_fields": ["issuer","counterparty","issue_date"],
        "anomalies": ["duplicate signature","amount mismatch"],
        "schema_errors": ["missing required field: issuer"],
        "completeness_score": 0.22
      }
    }
  ]' | python3 -m json.tool
