# Risk Agent API

AI-powered document analysis for summary generation, risk scoring, and automated recommendation.

This project implements a Decision, Summary & Risk Agent pipeline that:
- accepts standardized document payloads,
- computes a deterministic risk score,
- produces an `approve`/`review`/`reject` recommendation,
- and returns an LLM-generated summary.

---

## Features

- **Decision Agent** — deterministic risk scoring plus recommendation logic.
- **Summary Agent** — AI-generated document summaries via Ollama or Anthropic.
- **Risk Agent** — end-to-end orchestration for a single document or batched payloads.
- **Batch processing** — handle up to 20 documents in one request.
- **FastAPI** — production-ready API with Swagger UI and ReDoc.

---

## Project Structure

```
risk-agent/
├── app.py                    # Entry point that starts uvicorn
├── app_module/
│   └── main.py               # FastAPI app factory and router registration
├── agent_module/
│   ├── models.py             # Pydantic request/response schemas
│   ├── scoring.py            # Risk score computation and recommendation logic
│   └── decision_agent.py     # Agent orchestration: score → summary → response
├── routers/
│   ├── agent.py              # POST /api/v1/analyze and POST /api/v1/batch
│   └── health.py             # GET /health
├── services/
│   └── llm_service.py        # Pluggable Ollama / Anthropic summary service
├── data/
│   └── risk_agent.json       # Example request payload
├── tests/
│   ├── test_api.py
│   ├── test_models.py
│   ├── test_scoring.py
│   ├── conftest.py
│   ├── batch_test.py
│   └── test_examples.sh
├── pyproject.toml
└── requirements.txt
```

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Installation

### With uv (recommended)

```bash
git clone <repo-url>
cd risk-agent
uv sync
```

### With pip

```bash
pip install -r requirements.txt
```

---

## Running the Server

```bash
python app.py

# or via uv
uv run python app.py
```

Environment variables:

| Variable            | Default     | Description |
|---------------------|-------------|-------------|
| `PORT`              | `8000`      | API port |
| `UVICORN_RELOAD`    | `0`         | Set `1` to enable hot reload |
| `OLLAMA_URL`        | `http://127.0.0.1:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL`      | `llama2`    | Ollama model name |
| `ANTHROPIC_API_KEY` | *(not set)* | Optional Anthropic API key |
| `LLM_PROVIDER`      | `ollama` if `OLLAMA_URL` set, else `anthropic` | Preferred LLM provider |

If no LLM provider is configured, the service still returns a valid response with a fallback summary.

---

## API Reference

### `GET /health`

Returns service health metadata.

### `POST /api/v1/analyze`

Analyze a single document and return an agent response.

**Request body:**

```json
{
  "document_id": "DOC001",
  "standardized_data": {
    "document_type": "invoice",
    "issuer": "Acme Corp",
    "amount": 15000.0,
    "currency": "USD",
    "issue_date": "2024-01-15",
    "expiry_date": "2024-04-15",
    "counterparty": "Globex Ltd",
    "jurisdiction": "US",
    "metadata": {"po_number": "PO-9981"}
  },
  "validation_result": {
    "is_valid": true,
    "missing_fields": [],
    "anomalies": [],
    "schema_errors": [],
    "completeness_score": 0.97
  }
}
```

**Core response:**

```json
{
  "document_id": "DOC001",
  "summary": "...",
  "risk_score": 0.12,
  "recommendation": "approve",
  "confidence": 0.95
}
```

The full response also includes `risk_breakdown`, `reasoning`, `flags`, and `processed_at` for orchestration and auditability.

---

### `POST /api/v1/batch`

Process up to 20 documents concurrently. The request body is an array of the same objects accepted by `/analyze`.

---

## Risk Scoring

The composite risk score is computed as a weighted sum of four risk components:

| Component          | Weight | Description |
|--------------------|--------|-------------|
| `validation_risk`  | 30%    | Invalid documents and missing fields |
| `completeness_risk`| 25%    | Inverse of completeness score |
| `anomaly_risk`     | 25%    | Sigmoid penalty for anomalies |
| `schema_risk`      | 20%    | Linear penalty for schema errors |

Recommendation thresholds:

| Score Range | Recommendation |
|-------------|----------------|
| `0.00 – 0.25` | `approve` |
| `0.26 – 0.55` | `review` |
| `0.56 – 1.00` | `reject` |

---

## Testing

Run the test suite with:

```bash
pytest tests/
```

Or with uv:

```bash
uv run pytest
```

---

## Interactive Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## License

MIT
