# Demo Documentation

## Predictive Maintenance Intelligence System

---

### 1. Setup Overview

The demo application can be started locally in a few minutes. It requires Python (3.11 or above) and a local LLM runtime.

```
ollama pull gpt-oss:120b-cloud
ollama pull nomic-embed-text:v1.5

cd backend
python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env    
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Check is server running: http://localhost:8000/api/health
```

### 2. Authentication

The system uses token-based authentication. An engineer can log in using a predefined test account and receive an access token and refresh token. The access token must be passed in the Authorization header for all protected API calls.
For demo purpose I have create two accounts as follow:

admin: admin@pm-system.com 
pass: Admin@123

engineer: engineer@pm-system.com
pass: Engineer@123
---

### 3. Running an AI Diagnostic

The main demo flow is the diagnostic API.

When a diagnostic request is submitted with an equipment ID and a description, the system executes the full workflow. This includes checking current health data, retrieving relevant documents, generating a diagnosis, and deciding whether a work order is required.

For critical cases, the system automatically creates a work order and includes the reference ID in the response. The response also contains severity level, confidence score, and the sources used for diagnosis.

---

### 4. Viewing and Updating Work Orders

Auto-created work orders can be queried using a simple API endpoint. Results can be filtered based on severity.

Work order status can be updated as maintenance progresses, for example from OPEN to IN_PROGRESS. This simulates how engineers would track ongoing corrective actions.

---

### 5. RAG Evaluation (Admin)

An admin user can trigger a RAG evaluation run.

The evaluation executes a small set of predefined technical questions and measures how well the system retrieves relevant context and uses it in responses. Metrics such as faithfulness and context recall are returned.

This helps validate retrieval quality and system grounding.

---

### 6. Testing

Automated tests are provided for authentication, agent workflow, retrieval logic, and evaluation.

LLM and retrievers are mocked, allowing tests to run without requiring local models. This keeps test execution fast and deterministic.

---