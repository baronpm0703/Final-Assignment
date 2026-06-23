# Call Center Analytics Agent

FastAPI service for call center analytics with agentic chatbot over PostgreSQL.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for PostgreSQL)

## Setup

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Copy env file and fill in your keys
cp .env.example .env
```

Edit `.env` — fill in the required fields:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI provider) |
| `GEMINI_API_KEY` | Gemini API key (if using Gemini provider) |
| `LLM_PROVIDER` | `openai` or `gemini` |
| `LLM_MODEL` | e.g. `openai:gpt-4o-mini` or `gemini:gemini-2.0-flash` |

Database URLs can stay as default if using the provided Docker setup.

## Run

```bash
# 3. Start PostgreSQL
make docker-up

# 4. Initialize database schema + mock data
make init-db

# 5. Ingest knowledge base into pgvector
make ingest

# 6. Start dev server
make dev
```

API available at: `http://localhost:8000`

## Test

```bash
make test    # all tests
make lint    # ruff check
```

## Stop

```bash
make docker-down
```
