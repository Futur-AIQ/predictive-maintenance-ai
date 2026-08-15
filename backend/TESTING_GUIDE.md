# Testing Guide — Predictive Maintenance Intelligence System

A step-by-step guide to test every part of the backend using the NASA CMAPSS turbofan engine dataset (real Kaggle data or the synthetic copy already included).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [NASA CMAPSS Data Setup](#2-nasa-cmapss-data-setup)
3. [Start the Server](#3-start-the-server)
4. [Verify CMAPSS Data Loaded](#4-verify-cmapss-data-loaded)
5. [Authentication](#5-authentication)
6. [Equipment Health Endpoints](#6-equipment-health-endpoints)
7. [Diagnostic AI Agent — CRITICAL Scenario](#7-diagnostic-ai-agent--critical-scenario)
8. [Diagnostic AI Agent — Low Severity Scenario](#8-diagnostic-ai-agent--low-severity-scenario)
9. [More Diagnostic Test Cases](#9-more-diagnostic-test-cases)
10. [Work Order Management](#10-work-order-management)
11. [Diagnostic History](#11-diagnostic-history)
12. [RAG Evaluation (RAGAS)](#12-rag-evaluation-ragas)
13. [Swagger UI (No curl)](#13-swagger-ui-no-curl)
14. [Automated Test Suite](#14-automated-test-suite)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

### Python environment
```bash
# From backend/ directory
# Windows (Git Bash / PowerShell)
venv/Scripts/activate

# Linux / macOS
source venv/bin/activate
```

### `.env` file
Copy `.env.example` to `.env` and fill in at least one LLM:
```bash
cp .env.example .env
```

Minimum required fields in `.env`:
```
SECRET_KEY=change-this-to-any-32-char-random-string
DATABASE_URL=sqlite:///./data/pm_system.db
CHROMA_PERSIST_DIR=./chroma_db

# Pick at least ONE of these LLM options:
OLLAMA_BASE_URL=http://localhost:11434   # Option A (local, free)
OLLAMA_MODEL=llama3.2

ANTHROPIC_API_KEY=sk-ant-...             # Option B (cloud)
OPENAI_API_KEY=sk-...                    # Option C (fallback)
```

The system tries Ollama first, then Anthropic, then OpenAI — whichever is available.

---

## 2. NASA CMAPSS Data Setup

### Option A — Synthetic data (already included, zero setup)

The repository ships with synthetic CMAPSS FD001-format data covering **20 turbofan engines** with realistic HPC degradation patterns:

```
data/raw/nasa_cmapss/
  train_FD001.txt   — 4,974 rows (20 engines, run-to-failure)
  test_FD001.txt    — 2,969 rows (truncated mid-lifecycle snapshots)
  RUL_FD001.txt     — 20 ground-truth RUL values
  README.txt        — column descriptions
```

To regenerate if deleted:
```bash
venv/Scripts/python.exe scripts/generate_cmapss_data.py
```

### Option B — Real NASA CMAPSS from Kaggle (100 engines)

The real dataset has **100 engines** (vs 20 synthetic) and provides higher statistical variety.

**Step 1 — Get Kaggle API credentials**
1. Log in to [https://www.kaggle.com](https://www.kaggle.com)
2. Click your profile avatar → **Settings** → **API** section → **Create New Token**
3. A `kaggle.json` file downloads automatically

**Step 2 — Install the credentials**
```bash
# Windows
mkdir %USERPROFILE%\.kaggle
copy %USERPROFILE%\Downloads\kaggle.json %USERPROFILE%\.kaggle\kaggle.json

# Linux / macOS
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

**Step 3 — Download the dataset**
```bash
venv/Scripts/python.exe scripts/download_cmapss.py
```
This downloads from `behrad3d/nasa-cmaps` and extracts to `data/raw/nasa_cmapss/`.

**Step 4 — Clear cached ChromaDB and restart**
```bash
# Force re-ingestion with the new data
rm -rf chroma_db/
# Then restart the server (next section)
```

> **Note:** With 100 engines, equipment IDs Engine-01..20 map to the first 20 of the real dataset. The equipment list will still show 50 items total (20 turbofans + 15 pumps + 15 compressors).

---

## 3. Start the Server

```bash
# From backend/ directory
venv/Scripts/python.exe -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Startup sequence** (watch the log output):
```
INFO  Starting Predictive Maintenance Intelligence System...
INFO  Database initialized and seeded.
INFO  Starting data ingestion from ./data/raw
INFO  add_documents: 199 documents added to 'technical_docs'
INFO  add_documents: 50 documents added to 'maintenance_history'
INFO  CMAPSS data loaded: 20 engines from test set (./data/raw/nasa_cmapss/test_FD001.txt)
INFO  Uvicorn running on http://0.0.0.0:8000
```

Verify it's running:
```bash
curl http://localhost:8000/api/health
# → {"status":"ok","version":"1.0.0","timestamp":"..."}
```

---

## 4. Verify CMAPSS Data Loaded

Run this quick check before testing the API:

```bash
venv/Scripts/python.exe -c "
from src.data.cmapss_processor import cmapss
cmapss.load()
snaps = cmapss.get_all_snapshots()
print(f'Loaded {len(snaps)} engines')
for eid in sorted(snaps.keys()):
    s = snaps[eid]
    print(f'{s.equipment_id}: health={s.health_score:5.1f}%, rul={s.rul:3d} cycles, {s.status}')
"
```

**Expected output** (synthetic data):
```
Loaded 20 engines
Engine-01: health= 29.7%, rul= 93 cycles, CRITICAL
Engine-02: health= 21.7%, rul= 73 cycles, CRITICAL
Engine-03: health= 76.0%, rul=225 cycles, OK
Engine-04: health= 50.3%, rul=171 cycles, WARNING
Engine-05: health=  9.1%, rul= 20 cycles, CRITICAL   ← known bearing fault
Engine-06: health= 59.5%, rul=207 cycles, WARNING
Engine-07: health= 66.2%, rul=129 cycles, OK
Engine-08: health= 14.6%, rul= 22 cycles, CRITICAL
Engine-09: health= 53.5%, rul= 83 cycles, WARNING
Engine-10: health= 50.0%, rul= 78 cycles, WARNING
Engine-11: health= 33.9%, rul=102 cycles, WARNING
Engine-12: health= 58.6%, rul=157 cycles, WARNING
Engine-13: health= 13.1%, rul= 20 cycles, CRITICAL
Engine-14: health= 30.4%, rul=102 cycles, WARNING
Engine-15: health= 11.1%, rul= 20 cycles, CRITICAL   ← known bearing fault
Engine-16: health= 41.6%, rul= 64 cycles, WARNING
Engine-17: health= 77.5%, rul=269 cycles, OK
Engine-18: health= 16.5%, rul= 44 cycles, CRITICAL
Engine-19: health= 27.1%, rul= 69 cycles, CRITICAL
Engine-20: health= 28.1%, rul= 57 cycles, CRITICAL
```

**CMAPSS sensor baselines** (FD001, sea-level, HPC fault mode):
| Sensor | Baseline | Degraded direction | Meaning |
|--------|----------|--------------------|---------|
| T30 | 1589°R | **increases** (+50 at failure) | HPC outlet temperature |
| Ps30 | 47.5 psia | **decreases** (−3 at failure) | Static pressure at HPC |
| phi | 521.5 pps/psi | increases | Fuel-air ratio |
| BPR | 8.45 | decreases | Bypass ratio |
| W31 | 39.0 lbm/s | decreases | HPT coolant bleed |
| W32 | 23.0 lbm/s | decreases | LPT coolant bleed |

---

## 5. Authentication

All API endpoints (except `/api/health`) require a Bearer token.

### Login as engineer
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=engineer@pm-system.com&password=Engineer@123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {"id": 2, "email": "engineer@pm-system.com", "role": "engineer", ...}
}
```

### Login as admin
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@pm-system.com&password=Admin@123"
```

### Store tokens for subsequent commands
```bash
# Bash / Git Bash
TOKEN="<paste access_token here>"
ADMIN_TOKEN="<paste admin access_token here>"
```

### Other auth endpoints
```bash
# Get current user profile
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Refresh access token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Register a new user (admin only)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newengineer@test.com", "password": "Test@1234", "full_name": "Test Engineer", "role": "engineer"}'
```

---

## 6. Equipment Health Endpoints

### List all 50 equipment (sorted CRITICAL → WARNING → OK)
```bash
curl http://localhost:8000/api/equipment/ \
  -H "Authorization: Bearer $TOKEN"
```

Response excerpt:
```json
[
  {"equipment_id": "Engine-05", "equipment_type": "turbofan", "health_score": 9.1, "rul": 20, "status": "CRITICAL", ...},
  {"equipment_id": "Engine-15", "equipment_type": "turbofan", "health_score": 11.1, "rul": 20, "status": "CRITICAL", ...},
  ...
  {"equipment_id": "Engine-17", "equipment_type": "turbofan", "health_score": 77.5, "rul": 269, "status": "OK", ...}
]
```

### Get health for a specific engine
```bash
# CRITICAL engine (bearing fault, near end-of-life)
curl http://localhost:8000/api/equipment/Engine-05/health \
  -H "Authorization: Bearer $TOKEN"

# OK engine (early lifecycle, long RUL)
curl http://localhost:8000/api/equipment/Engine-17/health \
  -H "Authorization: Bearer $TOKEN"
```

### Get all 21 raw CMAPSS sensor readings
```bash
curl http://localhost:8000/api/equipment/Engine-05/sensors \
  -H "Authorization: Bearer $TOKEN"
```

Expected — note the clear HPC degradation signature:
```json
{
  "equipment_id": "Engine-05",
  "equipment_type": "turbofan",
  "current_cycle": 200,
  "max_cycle": 220,
  "rul": 20,
  "health_score": 9.1,
  "status": "CRITICAL",
  "sensors": {
    "T2":  444.77,   "T24": 642.66,
    "T30": 1639.69,  "T50": 1472.82,   ← T30 elevated (+50), showing HPC degradation
    "P2":  14.62,    "P15": 21.61,
    "P30": 525.83,   "Nf":  2387.73,
    "Nc":  9051.04,  "epr": 1.30,
    "Ps30": 44.74,   "phi": 539.87,    ← Ps30 decreased (−2.8), phi increased
    "NRf": 2387.73,  "NRc": 8150.59,
    "BPR":  7.98,    "farB": 0.030,    ← BPR decreased
    "htBleed": 376.2, "Nf_dmd": 2388.0,
    "PCNfR_dmd": 100.0,
    "W31": 37.42,    "W32": 22.16      ← coolant bleed flows decreased
  }
}
```

Compare with healthy **Engine-17** (cycle 78/347, rul=269):
```bash
curl http://localhost:8000/api/equipment/Engine-17/sensors \
  -H "Authorization: Bearer $TOKEN"
# T30 ≈ 1598.7 (near 1589 baseline), Ps30 ≈ 47.2 (near 47.5 baseline)
```

---

## 7. Diagnostic AI Agent — CRITICAL Scenario

This is the core feature. The LangGraph workflow runs 5 nodes: health_check → retrieve_context → diagnose → work_order → respond.

```bash
curl -X POST http://localhost:8000/api/diagnostic/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": "Engine-05",
    "query": "elevated vibration and bearing noise detected, fault code F006 triggered"
  }'
```

**Expected response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "equipment_id": "Engine-05",
  "diagnosis": "Bearing wear detected on LP shaft with HPC temperature anomaly...",
  "root_cause": "Insufficient lubrication leading to metal fatigue in bearing assembly",
  "recommended_action": "Immediate engine removal and bearing replacement required",
  "confidence_score": 0.92,
  "severity": "CRITICAL",
  "work_order_id": "7f3c1a2b-...",
  "work_order_created": true,
  "sources_used": ["turbofan_manual.txt", "maintenance_logs.jsonl", "fault_code_reference.txt"],
  "agent_steps": [
    "health_check: Engine-05 health=9.1%, CRITICAL, rul=20 cycles",
    "retrieve_context: Found 5 technical docs + 3 maintenance history records",
    "diagnose: LLM analysis complete, severity=CRITICAL, confidence=0.92",
    "work_order: Created work order <uuid>",
    "respond: Final response prepared"
  ],
  "created_at": "2026-02-24T11:30:00Z"
}
```

**What to verify:**
- `severity` = `"CRITICAL"`
- `confidence_score` ≥ 0.8
- `work_order_created` = `true`
- `work_order_id` is a non-null UUID
- `agent_steps` has ≥ 4 entries

---

## 8. Diagnostic AI Agent — Low Severity Scenario

```bash
curl -X POST http://localhost:8000/api/diagnostic/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": "Pump-03",
    "query": "slight noise during startup that clears after warm-up period, no pressure anomaly"
  }'
```

**Expected:**
- `severity`: `"LOW"` or `"MEDIUM"`
- `work_order_created`: `false`
- `work_order_id`: `null`

---

## 9. More Diagnostic Test Cases

| Equipment | Test Query | Expected Severity | Work Order? |
|-----------|-----------|-------------------|-------------|
| `Engine-15` | `"T30 temperature spike, bearing failure F006 recurring"` | CRITICAL | Yes |
| `Engine-03` | `"routine inspection, all sensor readings nominal"` | LOW | No |
| `Engine-17` | `"scheduled 200-cycle maintenance check"` | LOW | No |
| `Comp-01` | `"C500 high discharge pressure fault, compressor surge"` | HIGH | Yes |
| `Pump-07` | `"P302 mechanical seal leak, elevated vibration"` | HIGH | Yes |
| `Engine-08` | `"F008 bearing fault, rul=22 cycles remaining, urgent"` | CRITICAL | Yes |

### Batch test script
```bash
for EQ_QUERY in \
  "Engine-15|T30 temperature spike, bearing failure F006" \
  "Engine-03|routine inspection, all readings normal" \
  "Comp-01|C500 high discharge pressure fault" ; do
  EQ=$(echo $EQ_QUERY | cut -d'|' -f1)
  QUERY=$(echo $EQ_QUERY | cut -d'|' -f2)
  echo "--- Testing $EQ ---"
  curl -s -X POST http://localhost:8000/api/diagnostic/run \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"equipment_id\": \"$EQ\", \"query\": \"$QUERY\"}" \
    | python -m json.tool | grep -E '"severity"|"work_order_created"|"confidence_score"'
  echo ""
done
```

---

## 10. Work Order Management

### View all open work orders (auto-created by CRITICAL diagnostics)
```bash
curl "http://localhost:8000/api/workorders/?status=OPEN" \
  -H "Authorization: Bearer $TOKEN"
```

### Filter by severity
```bash
curl "http://localhost:8000/api/workorders/?severity=CRITICAL&page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Get a specific work order
```bash
curl "http://localhost:8000/api/workorders/<work_order_id>" \
  -H "Authorization: Bearer $TOKEN"
```

### Update work order status
Valid statuses: `OPEN` → `IN_PROGRESS` → `RESOLVED` → `CLOSED`

```bash
curl -X PATCH "http://localhost:8000/api/workorders/<work_order_id>/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}'

# Mark as resolved
curl -X PATCH "http://localhost:8000/api/workorders/<work_order_id>/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "RESOLVED"}'
```

### Delete a work order (admin only)
```bash
curl -X DELETE "http://localhost:8000/api/workorders/<work_order_id>" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# → 204 No Content
```

---

## 11. Diagnostic History

### All past sessions for an engine
```bash
# Engine-05 has recurring bearing faults in maintenance_logs.jsonl
curl "http://localhost:8000/api/diagnostic/history?equipment_id=Engine-05&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Paginated diagnostic history (all equipment)
```bash
curl "http://localhost:8000/api/diagnostic/history?page=1&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Get a single diagnostic session
```bash
curl "http://localhost:8000/api/diagnostic/<session_id>" \
  -H "Authorization: Bearer $TOKEN"
```

### Equipment maintenance history (from work orders)
```bash
curl "http://localhost:8000/api/equipment/Engine-05/history" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 12. RAG Evaluation (RAGAS)

Measures how well the hybrid RAG pipeline retrieves relevant context.

```bash
# Run full RAGAS evaluation — takes 1-2 minutes (admin only)
curl "http://localhost:8000/api/evaluation/run" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Response:
```json
{
  "faithfulness": 0.85,
  "answer_relevancy": 0.78,
  "context_precision": 0.82,
  "context_recall": 0.74,
  "timestamp": "2026-02-24T12:00:00Z",
  "sample_count": 5
}
```

**Metric guide:**
| Metric | Meaning | Target |
|--------|---------|--------|
| `faithfulness` | Answer grounded in retrieved context | > 0.75 |
| `answer_relevancy` | Answer relevance to the question | > 0.70 |
| `context_precision` | Retrieved docs actually needed | > 0.70 |
| `context_recall` | Needed docs were retrieved | > 0.65 |

```bash
# Retrieve the latest cached result (engineer access)
curl "http://localhost:8000/api/evaluation/latest" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 13. Swagger UI (No curl)

The fastest way to explore the API interactively:

1. Open **http://localhost:8000/docs** in your browser
2. Click **Authorize** (padlock icon, top right)
3. In the `OAuth2PasswordBearer` field enter: `Bearer <your_access_token>`
4. Click **Authorize** → **Close**
5. Expand any endpoint and click **Try it out** → **Execute**

The Swagger UI auto-populates request/response schemas and shows example values.

---

## 14. Automated Test Suite

```bash
# Run all 22 tests (from backend/ directory)
venv/Scripts/python.exe -m pytest tests/ -v
```

Expected output:
```
tests/test_agent.py::test_langgraph_workflow_critical_fault PASSED
tests/test_agent.py::test_langgraph_workflow_low_severity_no_work_order PASSED
tests/test_agent.py::test_work_order_persisted_to_db PASSED
tests/test_agent.py::test_graceful_degradation_on_api_failure PASSED
tests/test_auth.py::test_login_success PASSED
... (22 tests total)
============================== 22 passed in ~20s ==============================
```

Run a specific test file:
```bash
venv/Scripts/python.exe -m pytest tests/test_agent.py -v
venv/Scripts/python.exe -m pytest tests/test_rag.py -v
```

---

## 15. Troubleshooting

### LLM not responding / diagnostic hangs
The system tries Ollama → Anthropic → OpenAI in order.

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not running, start it (or skip and set ANTHROPIC_API_KEY in .env)
ollama serve
ollama pull llama3.2
```

If neither Ollama nor any API key is configured, diagnostics will fail with graceful error handling (agent returns `error` field in response).

### "Data already ingested" / stale ChromaDB
If you replace the raw data files but the old ChromaDB persists:
```bash
rm -rf chroma_db/
# Restart the server — it re-ingests automatically
```

### `CMAPSS data not found` warning on startup
The processor auto-generates synthetic data if `train_FD001.txt` is missing:
```bash
venv/Scripts/python.exe scripts/generate_cmapss_data.py
```

### `401 Unauthorized` on all requests
Token expires after 30 minutes. Re-login:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=engineer@pm-system.com&password=Engineer@123"
```

### Kaggle download fails
```
Error: 403 Forbidden — dataset not found
```
- Verify `~/.kaggle/kaggle.json` exists and is valid
- Check dataset slug: must be exactly `behrad3d/nasa-cmaps`
- Accept dataset terms at: https://www.kaggle.com/datasets/behrad3d/nasa-cmaps

---

## Quick Reference

### Default Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@pm-system.com | Admin@123 |
| Engineer | engineer@pm-system.com | Engineer@123 |

### Equipment IDs
| Type | IDs |
|------|-----|
| Turbofan (CMAPSS) | Engine-01 to Engine-20 |
| Pump (simulated) | Pump-01 to Pump-15 |
| Compressor (simulated) | Comp-01 to Comp-15 |

### Key Turbofan Engines for Testing
| Engine | Health | Status | Best for |
|--------|--------|--------|----------|
| Engine-05 | 9.1% | CRITICAL | Bearing fault diagnostics, auto work order |
| Engine-15 | 11.1% | CRITICAL | Recurring bearing failure scenarios |
| Engine-08 | 14.6% | CRITICAL | Low RUL alert testing |
| Engine-03 | 76.0% | OK | Healthy engine baseline |
| Engine-17 | 77.5% | OK | High RUL, no-fault diagnostic |
| Engine-04 | 50.3% | WARNING | Mid-lifecycle, borderline diagnostics |

### Severity → Work Order Logic
| Diagnostic severity | Work order auto-created? |
|--------------------|--------------------------|
| CRITICAL | Yes |
| HIGH | Yes |
| MEDIUM | No |
| LOW | No |
