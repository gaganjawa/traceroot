# TraceRoot Project Board

## Project

**TraceRoot — Evidence-Grounded Production Incident Investigator**

Research Question:

> Can agentic evidence gathering improve root-cause identification and evidence grounding compared with knowledge-only RAG for software production incidents?

---

## Board Summary

| Epic | Status |
|---|---|
| Epic 0 — Foundation | ✅ DONE |
| Epic 1 — Synthetic Incident Environment | ✅ DONE |
| Epic 2 — RAG Baseline | ✅ DONE |
| Epic 3 — Operational Evidence Tools | 🟡 IN PROGRESS |
| Epic 4 — Agentic Investigation | ⬜ TODO |
| Epic 5 — Evaluation Framework | ⬜ TODO |
| Epic 6 — Comparative Experiments | ⬜ TODO |
| Epic 7 — Delivery | ⬜ TODO |
| Epic 8 — MCP Integration | 🟣 STRETCH |

---

# Epic 0 — Foundation

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-001 | Project Setup | 1h | ✅ DONE |
| TR-002 | Core Domain Models | 1h | ✅ DONE |
| TR-003 | Evaluation Contracts | 1h | ✅ DONE |
| TR-004 | Incident Data Contract | 1h | ✅ DONE |

### TR-001 — Project Setup

Completed:
- Python 3.12 project
- `uv` dependency management
- `src` layout
- pytest
- environment template
- Git repository and GitHub remote

### TR-002 — Core Domain Models

Completed:
- `EvidenceType`
- `Evidence`
- `Incident`
- `GroundTruth`
- `RCAResult`
- Pydantic validation
- 12 tests passing at ticket completion

### TR-003 — Evaluation Contracts

Completed:
- `EvaluatorType`
- `MetricResult`
- `ExecutionMetrics`
- `EvaluationResult`
- Evaluation package under `src/traceroot/evaluation`
- 17 tests passing at ticket completion

### TR-004 — Incident Data Contract

Completed:
- Separate agent-visible incident data from hidden ground truth
- `LogEntry`
- `MetricEntry`
- `DeploymentEntry`
- `CodeChangeEntry`
- `IncidentDataset`
- `load_incident()`
- `load_incident_dataset()`
- JSONL log loading
- JSON array loading for metrics/deployments/changes
- Dataset loader tests
- Ground truth excluded from `IncidentDataset`

---

# Epic 1 — Synthetic Incident Environment

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-005 | Initial Incident Dataset | 2h | ✅ DONE |
| TR-006 | Distractors & Dataset Validation | 1h | ✅ DONE |
| TR-007 | Engineering Knowledge Corpus | 2h | ✅ DONE |

### TR-005 — Initial Incident Dataset

Completed:
- 3 synthetic incidents
- Different root-cause categories
- Logs, metrics, deployments and code changes
- Hidden ground truth
- Stable evidence IDs
- Agent-visible data separated from evaluator ground truth

### TR-006 — Distractors & Dataset Validation

Completed:
- Plausible non-causal evidence
- Dataset consistency validator
- Evidence ID validation
- Supporting evidence validation
- Required evidence-surface validation
- 27 tests passing across project at ticket completion

### TR-007 — Engineering Knowledge Corpus

Completed:
- Architecture documentation
- Checkout runbook
- Payment runbook
- Order-processing runbook
- Incident-investigation guide
- YAML metadata
- No incident-specific ground-truth leakage

---

# Epic 2 — RAG Baseline

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-008 | Document Loading & Chunking | 1h | ✅ DONE |
| TR-009 | Embeddings + Qdrant Indexing | 1.5h | ✅ DONE |
| TR-010 | Semantic Retriever | 1.5h | ✅ DONE |
| TR-011 | Retrieval Evaluation Dataset | 1h | ✅ DONE |
| TR-012 | Recall@K Evaluator | 1h | ✅ DONE |
| TR-013 | Vanilla RAG Baseline | 2h | ✅ DONE |
| TR-014 | Baseline Experiment Tracking | 1h | ✅ DONE |

### TR-008 — Document Loading & Chunking

Completed:
- Markdown knowledge-document loading
- YAML front-matter parsing
- Required metadata validation
- Deterministic corpus loading
- Word-based overlapping chunking
- Deterministic chunk IDs
- Source metadata preservation
- Chunking parameter validation
- 33 tests passing across project at ticket completion

### TR-009 — Embeddings + Qdrant Indexing

Completed:
- OpenAI embedding integration
- `text-embedding-3-small`
- 1536-dimensional vectors
- Single and batch embedding
- Qdrant collection creation
- Cosine vector configuration
- Deterministic UUID5 point IDs
- `KnowledgeChunk` metadata stored as Qdrant payload
- Batch chunk indexing
- Repeatable upserts without duplicate accumulation
- OpenAI mocked in unit tests
- In-memory Qdrant used in unit tests
- End-to-end manual ingestion verified
- 5 knowledge documents indexed successfully
- 42 tests passing across project at ticket completion

### TR-010 — Semantic Retriever

Completed:
- Natural-language query embedding
- Qdrant cosine similarity retrieval
- Configurable top-K
- `KnowledgeChunk` reconstruction from Qdrant payload
- Similarity score preservation
- Query and top-K validation
- In-memory Qdrant integration tests
- OpenAI embedding mocked in unit tests
- Real knowledge-corpus retrieval manually verified
- 47 tests passing across project at ticket completion

### TR-011 — Retrieval Evaluation Dataset

Completed:
- Fixed 10-query retrieval benchmark
- Coverage across all five knowledge documents
- Varied natural-language query phrasing
- Explicit relevant-source labels
- Typed `RetrievalEvaluationCase` model
- Non-empty relevant-source validation
- Evaluation dataset loader
- Loader and validation tests
- 52 tests passing across project at ticket completion

### TR-012 — Recall@K Evaluator

Completed:
- Deterministic Recall@K calculation
- Configurable K
- Unique-source matching
- Duplicate retrieval protection
- Full, partial and zero-recall tests
- K-boundary behavior tests
- Invalid K validation
- Empty relevant-source validation
- 60 tests passing across project at ticket completion

### TR-013 — Vanilla RAG Baseline

Completed:
- Knowledge-only RCA baseline
- Incident title + description retrieval query
- Top-K semantic knowledge retrieval
- Chunk and source provenance in LLM context
- Structured `GeneratedRCA` output
- Mapping to domain `RCAResult`
- Retrieval provenance exposed without breaking the RCA API
- Lazy LLM client creation
- Structured-output failure handling
- No access to operational evidence
- No access to hidden ground truth
- Mocked OpenAI baseline tests
- Baseline orchestration tests
- Ruff formatting and linting introduced
- 67 tests passing across project at ticket completion
- Real INC-001 baseline run successfully verified

### TR-014 — Baseline Experiment Tracking

Completed:
- Structured `BaselineExperimentRecord`
- Separate `RetrievedKnowledge` provenance model
- Model and top-K tracking
- Retrieved chunk ID, source and similarity-score tracking
- Final `RCAResult` persistence
- Execution latency tracking
- Timezone-aware experiment timestamp
- JSON serialization
- Filesystem persistence with parent-directory creation
- Knowledge provenance kept separate from operational `evidence_ids`
- Real INC-001 experiment artifact successfully generated
- Real retrieval scores persisted
- Real LLM result persisted

---

# Epic 3 — Operational Evidence Tools

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-015 | Logs Tool | 45m | ✅ DONE |
| TR-016 | Metrics Tool | 45m | ✅ DONE |
| TR-017 | Deployment Tool | 45m | ✅ DONE |
| TR-018 | Git Changes Tool | 45m | ✅ DONE |
| TR-019 | Tool Interface + Tests | 1h | ⬜ TODO |

### TR-015 — Logs Tool

Completed:
- Deterministic incident log querying
- Optional service filtering
- Optional log-level filtering
- Optional message-content filtering
- AND semantics for combined filters
- Typed `LogEntry` results
- Stable evidence IDs preserved
- Existing incident dataset loader reused
- Incident-scoped evidence access
- Real INC-001 log query manually verified

### TR-016 — Metrics Tool

Completed:
- Deterministic incident metric querying
- Optional service filtering
- Optional metric-name filtering
- AND semantics for combined filters
- Typed `MetricEntry` results
- Stable evidence IDs preserved
- Original metric values and units preserved
- Existing incident dataset loader reused
- Incident-scoped evidence access
- Real INC-001 metric query manually verified
- 95 tests passing across project at ticket completion

### TR-017 — Deployment Tool

Completed:
- Deterministic incident deployment querying
- Optional service filtering
- Typed `DeploymentEntry` results
- Stable deployment evidence IDs preserved
- Original version, timestamp and description preserved
- Existing incident dataset loader reused
- Incident-scoped evidence access
- Real INC-002 payment-service deployment query manually verified
- 102 tests passing across project at ticket completion

### TR-018 — Git Changes Tool

Completed:
- Deterministic incident code-change querying
- Optional service filtering
- Typed `CodeChangeEntry` results
- Stable code-change evidence IDs preserved
- Original commit SHA preserved
- Original changed-file list preserved
- Original description and diff preserved
- Existing incident dataset loader reused
- Incident-scoped evidence access
- Real INC-002 payment-service code-change query manually verified
- 109 tests passing across project at ticket completion

---

# Epic 4 — Agentic Investigation

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-020 | LangGraph Investigation State | 1h | ⬜ TODO |
| TR-021 | Hypothesis Generation | 1h | ⬜ TODO |
| TR-022 | Tool Selection & Investigation Loop | 2h | ⬜ TODO |
| TR-023 | Hypothesis Verification/Rejection | 1h | ⬜ TODO |
| TR-024 | Investigation Guardrails | 1h | ⬜ TODO |
| TR-025 | Evidence-Grounded RCA Generation | 1h | ⬜ TODO |
| TR-026 | Investigation Trace Persistence | 45m | ⬜ TODO |

---

# Epic 5 — Evaluation Framework

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-027 | DeepEval Setup | 1h | ⬜ TODO |
| TR-028 | Root-Cause Accuracy Evaluator | 1h | ⬜ TODO |
| TR-029 | Evidence Precision & Recall | 1h | ⬜ TODO |
| TR-030 | DeepEval Faithfulness | 1h | ⬜ TODO |
| TR-031 | DeepEval Relevancy | 1h | ⬜ TODO |
| TR-032 | Agent Trace Evaluator | 1.5h | ⬜ TODO |
| TR-033 | Efficiency Instrumentation | 1h | ⬜ TODO |
| TR-034 | Unified Evaluation Runner | 2h | ⬜ TODO |

---

# Epic 6 — Comparative Experiments

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-035 | Expand Final Evaluation Dataset | 2h | ⬜ TODO |
| TR-036 | Run RAG vs Agent Evaluation | 1h | ⬜ TODO |
| TR-037 | Failure Analysis | 1h | ⬜ TODO |
| TR-038 | Evidence-Driven Improvement | 1.5h | ⬜ TODO |
| TR-039 | Re-evaluate & Compare | 1h | ⬜ TODO |

---

# Epic 7 — Delivery

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-040 | README + Architecture + Results | 2h | ⬜ TODO |
| TR-041 | 3-Minute Demo | 1h | ⬜ TODO |

---

# Epic 8 — Optional MCP Integration

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-042 | MCP Evidence Server | 2h | 🟣 STRETCH |
| TR-043 | LangGraph ↔ MCP Integration | 1h | 🟣 STRETCH |

MCP must not delay the core experiment.

---

# Kanban

## 🟡 In Progress

- None — TR-018 checkpoint ready to commit

## ⬜ Next Up

- TR-019 — Tool Interface + Tests

## ✅ Done

- TR-001 — Project Setup
- TR-002 — Core Domain Models
- TR-003 — Evaluation Contracts
- TR-004 — Incident Data Contract
- TR-005 — Initial Incident Dataset
- TR-006 — Distractors & Dataset Validation
- TR-007 — Engineering Knowledge Corpus
- TR-008 — Document Loading & Chunking
- TR-009 — Embeddings + Qdrant Indexing
- TR-010 — Semantic Retriever
- TR-011 — Retrieval Evaluation Dataset
- TR-012 — Recall@K Evaluator
- TR-013 — Vanilla RAG Baseline
- TR-014 — Baseline Experiment Tracking
- TR-015 — Logs Tool
- TR-016 — Metrics Tool
- TR-017 — Deployment Tool
- TR-018 — Git Changes Tool

## 🟣 Stretch

- TR-042 — MCP Evidence Server
- TR-043 — LangGraph ↔ MCP Integration

---

# Project Rules

1. Implement the simplest baseline before agent complexity.
2. Ground truth must never be accessible to the application or agent.
3. Synthetic ground truth must be fixed before evaluation.
4. Operational evidence tools must be deterministic.
5. RAG and agent approaches must use the same incidents.
6. Never fabricate evaluation results.
7. Evaluate retrieval independently from RCA generation.
8. Evaluate agent behavior as well as final answers.
9. Add complexity only when evaluation supports it.
10. MCP is optional and must not delay the core evaluation.

---

# Current Focus

**TR-018 — Git Changes Tool**

Goal:

Complete and commit deterministic code-change querying before starting TR-019.

Current state:
- implementation complete
- tests complete
- real INC-002 smoke test complete
- 109 tests passing
- ready to commit/push

Next after commit:

**TR-019 — Tool Interface + Tests**