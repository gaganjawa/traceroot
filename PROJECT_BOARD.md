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
| Epic 1 — Synthetic Incident Environment | 🟡 IN PROGRESS |
| Epic 2 — RAG Baseline | ⬜ TODO |
| Epic 3 — Operational Evidence Tools | ⬜ TODO |
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
- uv dependency management
- src layout
- pytest
- environment template
- Git repository and GitHub remote

### TR-002 — Core Domain Models

Completed:
- EvidenceType
- Evidence
- Incident
- GroundTruth
- RCAResult
- Pydantic validation
- 12 tests passing at ticket completion

### TR-003 — Evaluation Contracts

Completed:
- EvaluatorType
- MetricResult
- ExecutionMetrics
- EvaluationResult
- Evaluation package under `src/traceroot/evaluation`
- 17 tests passing at ticket completion

### TR-004 — Incident Data Contract

Completed:
- Separate agent-visible incident data from hidden ground truth
- LogEntry
- MetricEntry
- DeploymentEntry
- CodeChangeEntry
- IncidentDataset
- `load_incident()`
- `load_incident_dataset()`
- JSONL log loading
- JSON array loading for metrics/deployments/changes
- Dataset loader tests
- Ground truth excluded from IncidentDataset

---

# Epic 1 — Synthetic Incident Environment

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-005 | Initial Incident Dataset | 2h | ✅ DONE |
| TR-006 | Distractors & Dataset Validation | 1h | ✅ DONE |
| TR-007 | Engineering Knowledge Corpus | 2h | 🟡 IN PROGRESS |

## TR-005 — Initial Incident Dataset

Completed:
- 3 synthetic production incidents
- Different root-cause categories
- Logs
- Metrics
- Deployments
- Code changes
- Hidden ground truth
- Stable evidence IDs
- Agent-visible data physically separated from evaluator ground truth
- Incident descriptions contain symptoms rather than root-cause answers

Incidents:
- INC-001 — checkout latency / configuration regression
- INC-002 — payment authorization failures / code regression
- INC-003 — order processing backlog / downstream dependency failure

## TR-006 — Distractors & Dataset Validation

Completed:
- Plausible non-causal evidence
- Dataset consistency validator
- Incident/ground-truth ID validation
- Evidence ID uniqueness validation
- Supporting evidence existence validation
- Required evidence-surface validation
- Validator unit tests
- 27 tests passing across project at ticket completion

## TR-007 — Engineering Knowledge Corpus

Status: **IN PROGRESS**

Goals:
- Create synthetic engineering documentation
- Provide useful diagnostic knowledge without exposing incident answers
- Cover architecture, runbooks, and engineering guidance
- Add metadata suitable for retrieval
- Prepare corpus for RAG ingestion

---

# Epic 2 — RAG Baseline

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-008 | Document Loading & Chunking | 1h | ⬜ TODO |
| TR-009 | Embeddings + Qdrant Indexing | 1.5h | ⬜ TODO |
| TR-010 | Semantic Retriever | 1.5h | ⬜ TODO |
| TR-011 | Retrieval Evaluation Dataset | 1h | ⬜ TODO |
| TR-012 | Recall@K Evaluator | 1h | ⬜ TODO |
| TR-013 | Vanilla RAG Baseline | 2h | ⬜ TODO |
| TR-014 | Baseline Experiment Tracking | 1h | ⬜ TODO |

---

# Epic 3 — Operational Evidence Tools

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-015 | Logs Tool | 45m | ⬜ TODO |
| TR-016 | Metrics Tool | 45m | ⬜ TODO |
| TR-017 | Deployment Tool | 45m | ⬜ TODO |
| TR-018 | Git Changes Tool | 45m | ⬜ TODO |
| TR-019 | Tool Interface + Tests | 1h | ⬜ TODO |

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

## IN PROGRESS

- TR-007 — Engineering Knowledge Corpus

## NEXT UP

- TR-008 — Document Loading & Chunking
- TR-009 — Embeddings + Qdrant Indexing
- TR-010 — Semantic Retriever

## DONE

- TR-001 — Project Setup
- TR-002 — Core Domain Models
- TR-003 — Evaluation Contracts
- TR-004 — Incident Data Contract
- TR-005 — Initial Incident Dataset
- TR-006 — Distractors & Dataset Validation

## STRETCH

- TR-042 — MCP Evidence Server
- TR-043 — LangGraph ↔ MCP Integration

---

# Project Rules

1. Implement the simplest baseline before agent complexity.
2. Ground truth must never be accessible to the application or agent.
3. Synthetic ground truth must be fixed before model evaluation.
4. Operational evidence tools must be deterministic.
5. RAG and agent approaches must use the same incidents.
6. Never fabricate evaluation results.
7. Evaluate retrieval independently from RCA generation.
8. Evaluate agent behavior as well as final answers.
9. Add complexity only when evaluation supports it.
10. MCP is optional and must not delay the core evaluation.

---

# Current Focus

## TR-007 — Engineering Knowledge Corpus

Create the synthetic engineering documentation used by both the RAG baseline and the agent.

Initial corpus:
- Architecture documentation
- Checkout runbook
- Payment runbook
- Order-processing runbook
- General incident investigation guidance

Requirements:
- Markdown documents
- Useful diagnostic knowledge
- No incident-specific ground truth
- No direct answers to INC-001, INC-002, or INC-003
- Suitable metadata for later retrieval