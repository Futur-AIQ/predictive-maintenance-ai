# Architecture Decision Record

## Predictive Maintenance Knowledge Assistant

---

### 1. Problem Summary

As I working in the manufacturing industry : GMM PFaudler, I have identified the problem which should be solve using AI. I have done some research based on the problem statement and start collecting information. In manufacturing plants, maintenance engineers depend on sensor readings, equipment manuals, and past maintenance logs to identify machine failures. This information is usually spread across different systems and files, which makes diagnosis slow.

The goal of this application is to reduce the time required to understand failures, identify severity, and suggest corrective actions. When confidence is high, the system should also create a work order automatically to avoid further delay.

---

### 2. Architecture Choice

A hybrid architecture using Retrieval Augmented Generation (RAG) along with an agent-style workflow was selected. 

RAG ensures that answers are based on real maintenance documents instead of assumptions. The agent workflow supports multi-step decisions such as validating health data, performing diagnosis, and deciding whether a work order is required. This combination was considered the most practical approach. 

---

### 3. Key Design Decisions

#### Language Model

Local execution of the language model is preferred for data privacy and cost reasons. Cloud models are used only if the local model is not available.

Currently, I am using gpt-oss:120b-cloud model provided by the ollama cloud. This cloud provide better model inferences with some free requestes. For development and testing purpuses, I use this model.

The models run with temperature set to zero to ensure consistent and repeatable outputs. A simple model availability check is performed before execution.

---

#### Vector Database

ChromaDB is used as the vector store. It is lightweight, runs locally, and integrates well with the selected framework.

For the expected data volume of this system, its performance is acceptable. A more scalable solution would be needed for large deployments.

---

#### Document Handling

Different document types are processed differently.

Manuals are split into chunks with overlap to preserve technical context. Fault codes are stored as single entries. Maintenance logs are stored per record. This approach improved retrieval quality during testing.

---

### 4. Workflow Design

The diagnostic flow is implemented as a step-based workflow.

The main steps are health data validation, document retrieval, diagnosis generation, and optional work order creation. Work orders are created only for high or critical severity cases.

Diagnosis and work order creation are kept separate to avoid unwanted side effects during testing.

---

### 5. Trade-offs

The system prioritizes accuracy and reliability over low response time. Running models locally increases latency but provides better control and privacy.

Caching is not implemented to avoid returning outdated diagnostic results.

---

### 6. Future Improvements

Future enhancements could include parallel retrieval, partial response streaming, and a feedback option for engineers.

Improved ranking models and better sensor data integration may further improve accuracy.

---

### 7. Production Notes

For production use, the system would need a scalable database, stronger authentication, proper secrets management, and monitoring.

Rate limiting and logging would also be required.

---

### 8. Success Criteria

Success will be measured by diagnosis accuracy, reduced time to diagnosis, low false-positive work orders, and system availability.

---
