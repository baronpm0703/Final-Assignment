# Call Center Analytics Agent

FastAPI service for call center analytics over PostgreSQL. The implementation follows
`spec/ARCHITECTURE_REVIEW.md` and currently covers phases 0-9 as an MVP.

## What Is Included

- FastAPI API: `/api/health`, `/api/config`, `/api/chat`
- Pydantic settings from `.env`
- Provider-agnostic LLM registry with mock, OpenAI, and Gemini adapters
- Markdown knowledge base with deterministic offline retrieval
- Intent router for `data_query`, `out_of_scope`, `chitchat`, and unsafe input
- Data agent with RAG retrieval, validated SQL execution, response formatting, and visualization metadata
- Data agent system prompt at `prompts/data_agent_system.md`
- Conversation memory with recent window, compaction, and summary cache
- PostgreSQL schema, mock data, read-only role, and `kb_chunks` pgvector table
- Unit and integration tests

## Setup

```bash
uv sync --extra dev
cp .env.example .env
```

The project targets Python 3.11+. Use `uv run ...` or the Makefile commands so imports resolve
from the project root and the uv-managed `.venv`.

## Run Tests

```bash
make test
make lint
```

The database integration test skips automatically when PostgreSQL is not running.

## Run With PostgreSQL

```bash
make docker-up
make init-db
make ingest
make dev
```

API base URL: `http://localhost:8000`

Example request:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"demo","message":"Phan tich chi so Abandon theo tung thang tu 1.2026-3.2026"}'
```

## Configuration

Key environment variables:

- `DATABASE_URL`
- `DATABASE_READONLY_URL`
- `SQL_MAX_LIMIT`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `MEMORY_WINDOW_SIZE`

Default LLM mode is `mock:offline`, so local tests do not call external APIs.
The data agent still calls the configured LLM provider in this mode; the mock provider returns
an offline reasoning note while preserving the same prompt flow.

## Notes

SSE streaming is intentionally deferred. The MVP returns non-streaming JSON with
`answer`, `visualization`, `sql_executed`, and `reasoning_steps`.
