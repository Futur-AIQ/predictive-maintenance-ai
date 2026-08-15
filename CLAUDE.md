# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# From predictive-maintenance-ai/backend/
# Create venv with Python 3.11 (required — pydantic-core/tokenizers have no
# prebuilt wheels for 3.14+, and building them from source fails since PyO3
# caps out at 3.13)
python3.11 -m venv venv

# Activate venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows CMD/PowerShell
source venv/Scripts/activate  # Windows Git Bash

# Install dependencies
pip install -r requirements.txt

# Run dev server (starts on port 8000, auto-ingests data on first startup)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_auth.py -v

# Run a single test function
pytest tests/test_auth.py::test_login_success -v

# Run Alembic migrations (if using migration workflow)
alembic upgrade head

# API docs available at
# http://localhost:8000/docs
```

### Frontend

```bash
# From predictive-maintenance-ai/frontend/
npm install
npm run dev        # starts on port 3000
npm run build
npm run lint
```

Requires `NEXT_PUBLIC_API_URL` pointing to the backend (default: `http://localhost:8000`).
NextAuth requires `NEXTAUTH_SECRET` and `NEXTAUTH_URL=http://localhost:3000`.

### Docker (full stack)

```bash
# From predictive-maintenance-ai/
docker-compose up --build
```

## Architecture

### Monorepo Layout

```
predictive-maintenance-ai/
├── backend/     # Python FastAPI + LangGraph + ChromaDB
└── frontend/    # Next.js 15 + React 19 + shadcn/ui
```

### Backend (`backend/src/`)

**Entry point**: `src/api/main.py` — FastAPI app with lifespan that runs `init_db()` + `run_ingestion()` on startup.

**Startup sequence**:
1. `database.init_db()` — creates SQLite tables, seeds 2 default users
2. `data_ingestion.run_ingestion()` — processes raw data files → ChromaDB (skipped if already populated)

**LLM Priority** (configured in `src/agents/nodes._get_llm()`):
1. **OpenRouter** — primary; requires `OPENROUTER_API_KEY` + `OPENROUTER_MODEL`
2. **Anthropic Claude claude-sonnet-4-5** — secondary
3. **OpenAI gpt-4o-mini** — fallback

The RAGAS evaluation judge LLM follows this same chain. RAG embeddings run locally via `all-MiniLM-L6-v2` (no external server or API key required).

**Data flow for a diagnostic request**:
```
POST /api/diagnostic/run
  → diagnostic.py router
  → agents/graph.py run_diagnostic()
  → StateGraph: health_check → retrieve_context → diagnose → [work_order] → respond
  → DiagnosticSession saved to SQLite
  → returns DiagnosticResponse
```

**RAG pipeline** (`src/rag/`):
- `document_processor.py` — header-level split then char split (1024 chars, 200 overlap) for manuals; one-per-row for fault codes; one-per-entry for logs
- `vector_store.py` — ChromaDB with `all-MiniLM-L6-v2` embeddings; collections: `technical_docs`, `maintenance_history`
- `retriever.py` — HybridRetriever: vector (ChromaDB) + BM25/Okapi merged via Reciprocal Rank Fusion → fault-code priority boost → optional cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)

**LangGraph agent** (`src/agents/`):
- `state.py` — AgentState TypedDict (all fields Optional except equipment_id/user_query/messages/agent_steps)
- `tools.py` — 5 @tool functions; `create_work_order` imports DB session inside function to avoid circular imports
- `nodes.py` — 5 nodes; `diagnose_node` expects LLM to return strict JSON; falls back gracefully on parse errors
- `graph.py` — conditional edge on severity: HIGH/CRITICAL → work_order_node, else → respond_node

**Auth** — JWT (HS256), 30min access / 7-day refresh. Admin-only: POST /api/auth/register.

**Equipment health** — Simulated deterministically via `random.seed(hash(equipment_id) % 10000)` in `routers/equipment.py`. Equipment IDs: Engine-01..20, Pump-01..15, Comp-01..15. Engine-01..20 use real NASA CMAPSS sensor data; pumps/compressors are fully simulated.

**Useful equipment IDs for testing**:
- Engine-05, Engine-15 → CRITICAL health (good for fault/work-order tests)
- Engine-03, Engine-17 → OK health (good for healthy baseline tests)

**Frontend** (`frontend/src/`):
- `app/` — Next.js App Router; `(auth)/login` and `(dashboard)/` route groups
- `components/` — domain components (diagnostic, equipment, workorders, evaluation) + `ui/` (shadcn)
- `lib/api.ts` — Axios instance with Bearer token injection; `NEXT_PUBLIC_API_URL` configures base URL
- `store/` — Zustand state management
- Auth handled via NextAuth.js 5 (`app/api/auth/[...nextauth]/`)

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `OPENROUTER_API_KEY` | OpenRouter API key (primary LLM) |
| `OPENROUTER_MODEL` | OpenRouter model name (primary LLM) |
| `ANTHROPIC_API_KEY` | Anthropic API key (secondary LLM) |
| `OPENAI_API_KEY` | OpenAI API key (fallback LLM) |
| `DATABASE_URL` | SQLite path (default: sqlite:///./data/pm_system.db) |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path (default: ./chroma_db) |
| `CORS_ORIGINS` | Allowed CORS origins (default: http://localhost:3000) |

### Default Credentials (seeded on first startup)

| Role     | Email                  | Password     |
|----------|------------------------|--------------|
| admin    | admin@pm-system.com    | Admin@123    |
| engineer | engineer@pm-system.com | Engineer@123 |

### Test Strategy

- Tests use in-memory SQLite (no file I/O)
- LLM calls are mocked via `patch("src.agents.nodes._get_llm")`
- RAG retriever is mocked via `patch("src.agents.tools.retriever")`
- `conftest.py` fixtures: `client`, `admin_user`, `engineer_user`, `admin_token`, `engineer_token`, `mock_llm`
- See `backend/TESTING_GUIDE.md` for detailed test scenarios and coverage notes
