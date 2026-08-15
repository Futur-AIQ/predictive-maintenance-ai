# Predictive Maintenance Intelligence System

A production-quality full-stack AI application for industrial equipment fault diagnosis using Hybrid RAG + LangGraph agentic workflows.

## Overview

The system diagnoses equipment faults by retrieving relevant technical documentation, running an LLM-powered analysis through a stateful multi-step agent, and automatically creating work orders for high-severity issues. Engineers interact through a modern dashboard; the backend handles all AI orchestration transparently.

## Architecture

```
predictive-maintenance-ai/
├── backend/        # Python FastAPI + LangGraph + ChromaDB RAG
├── frontend/       # Next.js 15 + shadcn/ui + Tailwind CSS
└── docker-compose.yml
```

### Backend (`backend/src/`)

**Entry point**: `src/api/main.py` — FastAPI app with a lifespan that runs `init_db()` + `run_ingestion()` on startup.

**Startup sequence**:
1. `database.init_db()` — creates SQLite tables, seeds 2 default users
2. `data_ingestion.run_ingestion()` — processes raw docs → ChromaDB (skipped if already populated)

**LLM priority** (configured in `src/agents/nodes._get_llm()`):
1. **OpenRouter** — primary; requires `OPENROUTER_API_KEY` + `OPENROUTER_MODEL`
2. **Anthropic Claude claude-sonnet-4-5** — secondary; requires `ANTHROPIC_API_KEY`
3. **OpenAI gpt-4o-mini** — fallback; requires `OPENAI_API_KEY`

The RAGAS evaluation judge LLM follows this same chain.

**Data flow for a diagnostic request**:
```
POST /api/diagnostic/run
  → diagnostic router
  → agents/graph.py run_diagnostic()
  → StateGraph: health_check → retrieve_context → diagnose → [work_order] → respond
  → DiagnosticSession saved to SQLite
  → DiagnosticResponse returned
```

**RAG pipeline** (`src/rag/`):
- `document_processor.py` — manuals: 1024-char chunks / 200 overlap; fault codes: one doc per row; logs: one doc per JSON line
- `vector_store.py` — ChromaDB with local `all-MiniLM-L6-v2` (HuggingFace/sentence-transformers) embeddings, no external server required; collections: `technical_docs`, `maintenance_history`
- `retriever.py` — HybridRetriever: vector (ChromaDB) + BM25/Okapi merged via Reciprocal Rank Fusion; fault-code queries get priority boost; optional cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)

**LangGraph agent** (`src/agents/`):
- `state.py` — `AgentState` TypedDict (all fields Optional except `equipment_id`, `user_query`, `messages`, `agent_steps`)
- `tools.py` — 5 `@tool` functions; `create_work_order` imports the DB session inside the function to avoid circular imports
- `nodes.py` — 5 nodes; `diagnose_node` expects strict JSON from the LLM; falls back gracefully on parse errors
- `graph.py` — conditional edge on severity: `HIGH`/`CRITICAL` → `work_order_node`, else → `respond_node`

**Auth** — JWT (HS256), 30 min access / 7 day refresh. Admin-only: `POST /api/auth/register`.

**Equipment** — 50 predefined units (Engine-01..20, Pump-01..15, Comp-01..15). Turbofans use NASA CMAPSS degradation data where available; all units fall back to deterministic simulation seeded by `hash(equipment_id)`.

### Frontend (`frontend/src/`)

Built with Next.js 15, React 19, TypeScript, Tailwind CSS 4, and shadcn/ui. Authentication via NextAuth v5.

**Pages** (all behind auth middleware):

| Route | Purpose |
|-------|---------|
| `/dashboard` | Stats overview, top equipment by health, recent work orders |
| `/dashboard/equipment` | Browse all 50 units, filter by status |
| `/dashboard/equipment/[id]` | Sensor readings, health trend, maintenance history |
| `/dashboard/diagnostic` | Run AI diagnostic, view agent steps and retrieved sources |
| `/dashboard/workorders` | Filter/update/delete work orders |
| `/dashboard/evaluation` | RAGAS metrics display, trigger evaluation (admin) |
| `/dashboard/admin` | User management (admin only) |

**API client** (`src/lib/api.ts`) — Axios with JWT interceptor; 401 responses redirect to `/login`.

---

## Quick Start

### Prerequisites

- **Python 3.11** (required — `pydantic-core`/`tokenizers` have no prebuilt wheels for 3.14+, and building them from source fails since PyO3 caps out at 3.13)
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key (recommended) **or** an Anthropic/OpenAI API key

RAG embeddings run locally via `sentence-transformers` — no external server or API key needed for that part.

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate          # macOS/Linux
# or: venv\Scripts\activate       # Windows CMD/PowerShell
# or: source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env              # then fill in your values
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
# Create frontend/.env.local (see Environment Variables below)
npm run dev
```

App: http://localhost:3000

### Docker (full stack)

```bash
docker-compose up --build
```

---

## Environment Variables

### Backend (`backend/.env`)

```bash
# Security
SECRET_KEY=<random 32+ char string>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database & storage
DATABASE_URL=sqlite:///./data/pm_system.db
CHROMA_PERSIST_DIR=./chroma_db

# LLM — priority: OpenRouter → Anthropic → OpenAI (at least one required)
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Data paths
RAW_DATA_DIR=./data/raw
PROCESSED_DATA_DIR=./data/processed

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=<random string>    # generate with: openssl rand -base64 32
NEXTAUTH_URL=http://localhost:3000
```

---

## Default Credentials

Seeded automatically on first startup.

| Role     | Email                  | Password     |
|----------|------------------------|--------------|
| admin    | admin@pm-system.com    | Admin@123    |
| engineer | engineer@pm-system.com | Engineer@123 |

---

## API Endpoints

All routes require a `Bearer` JWT token except `/api/auth/login` and `/api/health`.

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/login` | — | Obtain access + refresh tokens |
| POST | `/api/auth/register` | Admin | Create a new user |
| POST | `/api/auth/refresh` | — | Refresh access token |
| GET | `/api/auth/me` | Any | Current user profile |
| GET | `/api/equipment/` | Engineer | List all 50 equipment units |
| GET | `/api/equipment/{id}/health` | Engineer | Health score, status, RUL |
| GET | `/api/equipment/{id}/sensors` | Engineer | Live sensor readings |
| GET | `/api/equipment/{id}/history` | Engineer | Last 10 diagnostic sessions |
| POST | `/api/diagnostic/run` | Engineer | Run LangGraph diagnostic |
| GET | `/api/diagnostic/history` | Engineer | Paginated session history |
| GET | `/api/workorders/` | Engineer | List work orders (filterable) |
| PATCH | `/api/workorders/{id}/status` | Engineer | Update work order status |
| DELETE | `/api/workorders/{id}` | Admin | Delete work order |
| GET | `/api/evaluation/run` | Admin | Run RAGAS evaluation (~1-2 min) |
| GET | `/api/evaluation/latest` | Engineer | Most recent evaluation report |
| GET | `/api/health` | — | Health check |

---

## Key Features

- **Hybrid RAG**: ChromaDB vector search + BM25 keyword search fused via Reciprocal Rank Fusion, with fault-code boosting and optional cross-encoder reranking
- **LangGraph Agent**: 5-node stateful workflow — health check → retrieval → diagnosis → (conditional) work order → respond
- **NASA CMAPSS Data**: Real turbofan degradation curves for Remaining Useful Life estimation
- **Automatic Work Orders**: Created for `HIGH`/`CRITICAL` severity faults with priority scoring
- **RAGAS Evaluation**: Faithfulness, Answer Relevancy, Context Precision, Context Recall — judge LLM via OpenRouter/Anthropic/OpenAI, embeddings computed locally
- **JWT Auth**: Role-based access control (Admin / Engineer) with refresh token support
- **Graceful LLM Fallback**: OpenRouter → Anthropic → OpenAI

---

## Running Tests

```bash
cd backend

# All tests
pytest tests/ -v

# Single file
pytest tests/test_auth.py -v

# Single test
pytest tests/test_diagnostic.py::test_run_diagnostic_success -v
```

Test strategy: in-memory SQLite, mocked LLM via `patch("src.agents.nodes._get_llm")`, mocked RAG retriever via `patch("src.agents.tools.retriever")`.

---

## Raw Data Sources

Documents in `backend/data/raw/` are ingested into ChromaDB on first startup:

| File | Content |
|------|---------|
| `equipment_manual_turbofan.txt` | Turbofan specifications, vibration limits, maintenance intervals |
| `equipment_manual_pump.txt` | Centrifugal pump design, cavitation diagnosis |
| `equipment_manual_compressor.txt` | Reciprocating compressor overhaul procedures |
| `fault_code_reference.txt` | Pipe-delimited fault code database (F/P/C + 3 digits) |
| `maintenance_logs.jsonl` | Historical maintenance records (JSON Lines) |
| `nasa_cmapss/` | NASA CMAPSS turbofan run-to-failure dataset |

---

## Tech Stack

**Backend**: FastAPI 0.115 · LangGraph 0.2 · LangChain 0.3 · ChromaDB 0.5 · SQLAlchemy 2.0 · rank-bm25 · RAGAS 0.2 · sentence-transformers (cross-encoder) · Pydantic 2

**Frontend**: Next.js 15 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui · NextAuth v5 · Zustand · Recharts · Axios
