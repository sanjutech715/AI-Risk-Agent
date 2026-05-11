# Risk Agent API

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)](https://fastapi.tiangolo.com/)

AI-powered document analysis for summary generation, risk scoring, and automated recommendation.

This project implements a Decision, Summary & Risk Agent pipeline that:
- accepts standardized document payloads,
- computes a deterministic risk score,
- produces an `approve`/`review`/`reject` recommendation,
- and returns an LLM-generated summary.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Risk Scoring](#risk-scoring)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Decision Agent** — deterministic risk scoring plus recommendation logic.
- **Summary Agent** — AI-generated document summaries via Ollama or Anthropic.
- **Risk Agent** — end-to-end orchestration for a single document or batched payloads.
- **Batch processing** — handle up to 20 documents in one request.
- **FastAPI** — production-ready API with Swagger UI and ReDoc.

---

## Architecture

The Risk Agent API follows a modular architecture with clear separation of concerns:

### Core Components

1. **Routers** (`routes/`): Handle HTTP requests and responses
   - `agent.py`: Main API endpoints for document analysis
   - `health.py`: Health check endpoint

2. **Agent Module** (`core/agent/`): Business logic for risk assessment
   - `models.py`: Pydantic request/response schemas
   - `scoring.py`: Risk score calculation algorithms
   - `agent.py`: Orchestrates scoring and summary generation

3. **Core Services** (`core/`): Shared services and infrastructure
   - `llm_service.py`: LLM integration for document summarization
   - `database.py`: Database and session management
   - `cache.py`: Cache abstraction and Redis fallback

4. **Application** (`app/`): FastAPI application factory and startup
   - `main.py`: FastAPI app factory and router registration

### Data Flow

```
Request → Router → Decision Agent → Scoring → LLM Service → Response
```

### Key Design Principles

- **Modular**: Each component has a single responsibility
- **Testable**: Comprehensive test suite with pytest
- **Configurable**: Environment-based configuration
- **Observable**: Health checks and structured logging
- **Secure**: Input validation and error handling

---

## Project Structure

```
risk-agent/
├── run.py                    # Entry point that starts uvicorn
├── pyproject.toml
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   └── main.py               # FastAPI app factory and router registration
├── config.py                 # Application configuration via Pydantic settings
├── core/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py           # Orchestrates risk analysis
│   │   ├── models.py          # Request/response schemas
│   │   └── scoring.py         # Risk scoring logic
│   ├── cache.py              # Cache abstraction and Redis fallback
│   ├── database.py           # Database session management
│   ├── llm_service.py        # LLM summary generation
│   ├── middleware_logging.py
│   ├── rate_limiting.py
├── routes/
│   ├── __init__.py
│   ├── agent.py              # POST /api/v1/analyze and POST /api/v1/batch
│   └── health.py             # GET /health
├── data/
│   └── risk_agent.json       # Example request payload
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_api.py
```

---

## Requirements

- Python 3.11+
- Redis (optional; health checks degrade gracefully when unavailable)
- PostgreSQL / async database for full runtime

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Quick Start

Start the API server:

```bash
python run.py
```

Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

---

## Health Endpoints

- `GET /health` — basic service health
- `GET /health/detailed` — checks database, cache, and LLM dependencies

---

## API Endpoints

- `POST /api/v1/analyze` — analyze a single document
- `POST /api/v1/batch` — analyze multiple documents

---

## Testing

Run pytest:

```bash
pytest tests/test_api.py -q
```

---

## Project Layout

- `run.py` — entry point that starts Uvicorn
- `app/` — FastAPI application factory
- `core/` — services, auth, database, cache, and agent logic
- `routes/` — API routers
- `tests/` — automated tests
- `data/` — example request payloads

---

## Notes

- The app supports hot reload via `UVICORN_RELOAD=1 python run.py`
- Swagger docs are available at `/docs`
- Health checks are designed to tolerate transient cache or LLM failures by returning a degraded status rather than a hard 503 failure

If no LLM provider is configured, the service returns a valid response with a fallback summary.

---

## Running the Server

```bash
python run.py

# or via uv
uv run python run.py
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

## Data Models

### Request Models

#### DocumentAnalysisRequest

```python
class DocumentAnalysisRequest(BaseModel):
    document_id: str
    standardized_data: StandardizedData
    validation_result: ValidationResult
```

#### StandardizedData

```python
class StandardizedData(BaseModel):
    document_type: str  # e.g., "invoice", "contract"
    issuer: str
    amount: Optional[float]
    currency: Optional[str]
    issue_date: Optional[str]
    expiry_date: Optional[str]
    counterparty: Optional[str]
    jurisdiction: Optional[str]
    metadata: Dict[str, Any]
```

#### ValidationResult

```python
class ValidationResult(BaseModel):
    is_valid: bool
    missing_fields: List[str]
    anomalies: List[str]
    schema_errors: List[str]
    completeness_score: float  # 0.0 to 1.0
```

### Response Models

#### AgentResponse

```python
class AgentResponse(BaseModel):
    document_id: str
    summary: str
    risk_score: float  # 0.0 to 1.0
    recommendation: Literal["approve", "review", "reject"]
    confidence: float  # 0.0 to 1.0
    risk_breakdown: RiskBreakdown
    reasoning: str
    flags: List[str]
    processed_at: datetime
```

#### RiskBreakdown

```python
class RiskBreakdown(BaseModel):
    validation_risk: float
    completeness_risk: float
    anomaly_risk: float
    schema_risk: float
```

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

## Development

### Setting up Development Environment

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd risk-agent
   ```

2. Install dependencies with dev extras:
   ```bash
   uv sync --dev
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Run in development mode with hot reload:
   ```bash
   UVICORN_RELOAD=1 python run.py
   ```

### Code Quality

- **Linting**: Use `ruff` for fast Python linting
- **Formatting**: Use `black` for consistent code formatting
- **Type checking**: Use `mypy` for static type analysis

### Adding New Features

1. Create a feature branch: `git checkout -b feature/new-feature`
2. Write tests first (TDD approach)
3. Implement the feature
4. Update documentation
5. Run full test suite
6. Submit a pull request

---

## Deployment

### Docker Deployment

Build and run with Docker:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "run.py"]
```

```bash
docker build -t risk-agent .
docker run -p 8000:8000 risk-agent
```

### Production Considerations

- Set `UVICORN_RELOAD=0` for production
- Use a reverse proxy (nginx/Caddy) for SSL termination
- Configure proper logging and monitoring
- Set environment variables securely
- Use health checks for container orchestration

### Environment Variables for Production

```bash
export PORT=8000
export OLLAMA_URL=http://ollama-service:11434
export ANTHROPIC_API_KEY=your-api-key-here
export LLM_PROVIDER=anthropic
```

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

## Contributing

We welcome contributions! Please follow these guidelines:

### How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Update documentation as needed
7. Commit your changes: `git commit -m 'Add amazing feature'`
8. Push to the branch: `git push origin feature/amazing-feature`
9. Open a Pull Request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write comprehensive docstrings
- Maintain test coverage above 80%
- Use meaningful commit messages

### Reporting Issues

- Use GitHub Issues to report bugs
- Provide detailed steps to reproduce
- Include relevant error messages and logs
- Suggest potential solutions if possible

---

## License

MIT
