# Call Center Analytics Agent

FastAPI service for call center analytics over PostgreSQL. The implementation follows
`spec/ARCHITECTURE_REVIEW.md` and currently covers phases 0-9 as an MVP.

## What Is Included

- FastAPI API: `/api/health`, `/api/config`, `/api/chat`
- Pydantic settings from `.env`
- Provider-agnostic LLM registry with OpenAI and Gemini adapters
- Markdown knowledge base with deterministic offline retrieval
- Intent router for `data_query`, `out_of_scope`, `chitchat`, and unsafe input
- Data agent with RAG retrieval, validated SQL execution, response formatting, and visualization metadata
- Data agent system prompt at `prompts/data_agent_system.md`
- AgentScope 2.x ReAct runtime via `agentscope.agent.Agent`, `ReActConfig`, and `Toolkit`
- Domain manifest at `config/domain.yaml` to keep business-specific metadata outside Python code
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

- `DOMAIN_CONFIG_PATH`
- `DATABASE_URL`
- `DATABASE_READONLY_URL`
- `SQL_MAX_LIMIT`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `MEMORY_WINDOW_SIZE`

Default LLM mode is `openai:gpt-4o-mini`. Set `OPENAI_API_KEY` for OpenAI models or
`GEMINI_API_KEY` for Gemini models before starting the API.

The scoped data flow uses AgentScope's ReAct loop:

```text
route intent -> AgentScope Agent -> retrieve_knowledge tool
             -> answer_business_question or execute_sql tool
             -> final API response
```

`config/domain.yaml` is the manifest that points the generic workflow at the active
business domain. It defines the active knowledge folder, system prompt file, SQL schema
whitelist, router keywords, offline demo query plans, and clarification options. To adapt
the chatbot to another business, change `domain.yaml`, `knowledge/`, `prompts/`, and the
database schema/init files without changing the Python workflow code.

## Notes

SSE streaming is intentionally deferred. The MVP returns non-streaming JSON with
`answer`, `visualization`, `sql_executed`, and `reasoning_steps`.
