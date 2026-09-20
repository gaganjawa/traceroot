# TraceRoot — Project Board

> Evidence-Grounded Production Incident Investigator

## Status Legend

- ⬜ TODO
- 🟡 IN PROGRESS
- ✅ DONE
- 🟣 STRETCH

---

## Board Summary

| **Epic** | **Scope**                      | **Status**     |
| -------- | ------------------------------ | -------------- |
| Epic 0   | Foundation                     | 🟡 IN PROGRESS |
| Epic 1   | Synthetic Incident Environment | ⬜ TODO         |
| Epic 2   | RAG Baseline                   | ⬜ TODO         |
| Epic 3   | Operational Evidence Tools     | ⬜ TODO         |
| Epic 4   | Agentic Investigation          | ⬜ TODO         |
| Epic 5   | Evaluation Framework           | ⬜ TODO         |
| Epic 6   | Comparative Experiments        | ⬜ TODO         |
| Epic 7   | Delivery                       | ⬜ TODO         |
| Epic 8   | MCP Integration                | 🟣 STRETCH     |

---

# Epic 0 — Foundation

Build the contracts and project structure everything else depends on.

| **Status** | **Ticket** | **Task**               | **Estimate** |
| ---------- | ---------- | ---------------------- | ------------ |
| ✅         | TR-001     | Project Setup          | 1h           |
| ✅         | TR-002     | Core Domain Models     | 1h           |
| ✅         | TR-003     | Evaluation Contracts   | 1h           |
| 🟡         | TR-004     | Incident Data Contract | 1h           |

### TR-001 — Project Setup

**Status:** ✅ DONE  
**Estimate:** 1h

Set up the Python project, `uv`, pytest, Git repository, project structure,
environment configuration, and GitHub repository.

### TR-002 — Core Domain Models

**Status:** ✅ DONE  
**Estimate:** 1h

Define the fundamental domain objects used across TraceRoot.

Implemented:

- `EvidenceType`
- `Evidence`
- `Incident`
- `GroundTruth`
- `RCAResult`
- Pydantic validation
- Confidence validation (`0.0–1.0`)
- Domain model tests

**Result:** 12 tests passing at completion of TR-002.

### TR-003 — Evaluation Contracts

**Status:** ✅ DONE  
**Estimate:** 1h

Define structured contracts for evaluation results so baseline and agent
experiments can be compared consistently.

Implemented:

- `EvaluatorType`
  - `DETERMINISTIC`
  - `DEEPEVAL`
  - `LLM_JUDGE`
- `MetricResult`
  - metric name
  - score
  - pass/fail status
  - evaluator type
  - optional reason
- `ExecutionMetrics`
  - latency
  - input/output token usage
  - tool calls
  - investigation steps
- `EvaluationResult`
  - incident ID
  - approach
  - quality metrics
  - optional execution metrics
- Evaluation schema tests

**Result:** 18 tests passing at completion of TR-003.

### TR-004 — Incident Data Contract

**Status:** 🟡 IN PROGRESS  
**Estimate:** 1h

Define the on-disk structure and validation rules for synthetic incidents,
operational evidence, and hidden ground truth.

---

# Epic 1 — Synthetic Incident Environment

Create a controlled production-like environment without using company data.

| **Status** | **Ticket** | **Task**                         | **Estimate** |
| ---------- | ---------- | -------------------------------- | ------------ |
| ⬜         | TR-005     | Initial Incident Dataset         | 2h           |
| ⬜         | TR-006     | Distractors & Dataset Validation | 1h           |
| ⬜         | TR-007     | Engineering Knowledge Corpus     | 2h           |

### TR-005 — Initial Incident Dataset

Create the first synthetic incidents with logs, metrics, deployments,
code changes, and hidden ground truth.

### TR-006 — Distractors & Dataset Validation

Add realistic irrelevant/neutral evidence and validate that incidents do not
leak their answers.

### TR-007 — Engineering Knowledge Corpus

Create synthetic architecture documentation, runbooks, engineering guidance,
and historical incident documentation for retrieval.

---

# Epic 2 — RAG Baseline

Build the simplest viable knowledge-only RAG system before introducing agents.

| **Status** | **Ticket** | **Task**                     | **Estimate** |
| ---------- | ---------- | ---------------------------- | ------------ |
| ⬜         | TR-008     | Document Loading & Chunking  | 1h           |
| ⬜         | TR-009     | Embeddings + Qdrant Indexing | 1.5h         |
| ⬜         | TR-010     | Semantic Retriever           | 1.5h         |
| ⬜         | TR-011     | Retrieval Evaluation Dataset | 1h           |
| ⬜         | TR-012     | Recall@K Evaluator           | 1h           |
| ⬜         | TR-013     | Vanilla RAG Baseline         | 2h           |
| ⬜         | TR-014     | Baseline Experiment Tracking | 1h           |

### TR-008 — Document Loading & Chunking

Load the knowledge corpus and convert documents into chunks with useful
metadata.

### TR-009 — Embeddings + Qdrant Indexing

Generate embeddings and store searchable knowledge chunks in Qdrant.

### TR-010 — Semantic Retriever

Implement semantic knowledge retrieval with configurable `top_k`.

### TR-011 — Retrieval Evaluation Dataset

Create known query → relevant-document/chunk mappings.

### TR-012 — Recall@K Evaluator

Measure whether relevant knowledge appears within the top K retrieved chunks.

### TR-013 — Vanilla RAG Baseline

Implement:

```text
Incident → Knowledge Retrieval → LLM → RCA
```

No operational investigation tools.

### TR-014 — Baseline Experiment Tracking

Persist baseline outputs, retrieved evidence, latency, token usage, and other
experiment metadata.

---

# Epic 3 — Operational Evidence Tools

Expose production-like evidence through deterministic tools.

| **Status** | **Ticket** | **Task**               | **Estimate** |
| ---------- | ---------- | ---------------------- | ------------ |
| ⬜         | TR-015     | Logs Tool              | 45m          |
| ⬜         | TR-016     | Metrics Tool           | 45m          |
| ⬜         | TR-017     | Deployment Tool        | 45m          |
| ⬜         | TR-018     | Git Changes Tool       | 45m          |
| ⬜         | TR-019     | Tool Interface + Tests | 1h           |

### TR-015 — Logs Tool

Implement structured log querying with filters such as service, level, and
text matching.

### TR-016 — Metrics Tool

Expose incident metrics through deterministic queries.

### TR-017 — Deployment Tool

Expose deployment events relevant to an incident.

### TR-018 — Git Changes Tool

Expose recent synthetic code/configuration changes.

### TR-019 — Tool Interface + Tests

Standardize tool inputs/outputs and independently test each evidence source.

---

# Epic 4 — Agentic Investigation

Build a bounded LangGraph agent that actively investigates incidents.

| **Status** | **Ticket** | **Task**                            | **Estimate** |
| ---------- | ---------- | ----------------------------------- | ------------ |
| ⬜         | TR-020     | LangGraph Investigation State       | 1h           |
| ⬜         | TR-021     | Hypothesis Generation               | 1h           |
| ⬜         | TR-022     | Tool Selection & Investigation Loop | 2h           |
| ⬜         | TR-023     | Hypothesis Verification / Rejection | 1h           |
| ⬜         | TR-024     | Investigation Guardrails            | 1h           |
| ⬜         | TR-025     | Evidence-Grounded RCA Generation    | 1h           |
| ⬜         | TR-026     | Investigation Trace Persistence     | 45m          |

### TR-020 — LangGraph Investigation State

Model investigation state including hypotheses, observations, evidence,
tool history, and remaining step budget.

### TR-021 — Hypothesis Generation

Generate plausible root-cause hypotheses from the incident and currently
available evidence.

### TR-022 — Tool Selection & Investigation Loop

Allow the agent to decide which evidence source to inspect next.

### TR-023 — Hypothesis Verification / Rejection

Use gathered evidence to support, weaken, or reject hypotheses.

### TR-024 — Investigation Guardrails

Bound the investigation using step limits and loop/repeated-call protection.

### TR-025 — Evidence-Grounded RCA Generation

Generate the final RCA with explicit references to evidence gathered during
the investigation.

### TR-026 — Investigation Trace Persistence

Persist the investigation path for debugging and evaluation.

---

# Epic 5 — Evaluation Framework

Evaluate both final RCA quality and the investigation process.

| **Status** | **Ticket** | **Task**                      | **Estimate** |
| ---------- | ---------- | ----------------------------- | ------------ |
| ⬜         | TR-027     | DeepEval Setup                | 1h           |
| ⬜         | TR-028     | Root-Cause Accuracy Evaluator | 1h           |
| ⬜         | TR-029     | Evidence Precision & Recall   | 1h           |
| ⬜         | TR-030     | DeepEval Faithfulness         | 1h           |
| ⬜         | TR-031     | DeepEval Relevancy            | 1h           |
| ⬜         | TR-032     | Agent Trace Evaluator         | 1.5h         |
| ⬜         | TR-033     | Efficiency Instrumentation    | 1h           |
| ⬜         | TR-034     | Unified Evaluation Runner     | 2h           |

### TR-027 — DeepEval Setup

Configure DeepEval and establish the evaluation test structure.

### TR-028 — Root-Cause Accuracy Evaluator

Compare predicted root cause against hidden ground truth.

### TR-029 — Evidence Precision & Recall

Measure whether the system used the correct supporting evidence.

### TR-030 — DeepEval Faithfulness

Measure whether generated conclusions are grounded in supplied context.

### TR-031 — DeepEval Relevancy

Measure whether the RCA directly addresses the incident.

### TR-032 — Agent Trace Evaluator

Evaluate tool selection, repeated calls, investigation path, and evidence
gathering behavior.

### TR-033 — Efficiency Instrumentation

Capture investigation steps, tool calls, latency, and token/cost information.

### TR-034 — Unified Evaluation Runner

Run systems against the same evaluation dataset and produce comparable
structured results.

---

# Epic 6 — Comparative Experiments

Run the actual experiment required by the capstone.

| **Status** | **Ticket** | **Task**                        | **Estimate** |
| ---------- | ---------- | ------------------------------- | ------------ |
| ⬜         | TR-035     | Expand Final Evaluation Dataset | 2h           |
| ⬜         | TR-036     | Run RAG vs Agent Evaluation     | 1h           |
| ⬜         | TR-037     | Failure Analysis                | 1h           |
| ⬜         | TR-038     | Evidence-Driven Improvement     | 1.5h         |
| ⬜         | TR-039     | Re-evaluate & Compare           | 1h           |

### TR-035 — Expand Final Evaluation Dataset

Expand the dataset to approximately 8–12 incidents while keeping ground truth
hidden from the application.

### TR-036 — Run RAG vs Agent Evaluation

Run both approaches against the same incidents:

A. Knowledge-only RAG  
B. Agentic evidence gathering

### TR-037 — Failure Analysis

Inspect incorrect RCAs, retrieval failures, unsupported claims, unnecessary
tool calls, and other measurable failure modes.

### TR-038 — Evidence-Driven Improvement

Make one or more targeted improvements justified by observed evaluation
failures.

### TR-039 — Re-evaluate & Compare

Repeat the experiment and compare measured results before and after the
improvement.

---

# Epic 7 — Delivery

Package the project for review and demonstration.

| **Status** | **Ticket** | **Task**                        | **Estimate** |
| ---------- | ---------- | ------------------------------- | ------------ |
| ⬜         | TR-040     | README + Architecture + Results | 2h           |
| ⬜         | TR-041     | 3-Minute Demo                   | 1h           |

### TR-040 — README + Architecture + Results

Document the problem, architecture, design decisions, evaluation methodology,
results, limitations, and failure analysis.

### TR-041 — 3-Minute Demo

Prepare a concise demonstration showing an incident investigation and the
RAG-vs-agent comparison.

---

# Epic 8 — Optional MCP Integration

> 🟣 STRETCH SCOPE — only start after the core project and evaluation work.

| **Status** | **Ticket** | **Task**                    | **Estimate** |
| ---------- | ---------- | --------------------------- | ------------ |
| 🟣         | TR-042     | MCP Evidence Server         | 2h           |
| 🟣         | TR-043     | LangGraph ↔ MCP Integration | 1h           |

### TR-042 — MCP Evidence Server

Expose TraceRoot evidence tools through an MCP server while preserving the
same underlying deterministic evidence layer.

### TR-043 — LangGraph ↔ MCP Integration

Allow the investigation agent to access evidence through MCP and verify that
the abstraction does not change investigation correctness.

---

# Kanban

## 🟡 In Progress

- TR-004 — Incident Data Contract

## ⬜ Next Up

- TR-005 — Initial Incident Dataset
- TR-006 — Distractors & Dataset Validation
- TR-007 — Engineering Knowledge Corpus

## ✅ Done

- TR-001 — Project Setup
- TR-002 — Core Domain Models
- TR-003 — Evaluation Contracts

## 🟣 Stretch

- TR-042 — MCP Evidence Server
- TR-043 — LangGraph ↔ MCP Integration

---

# Project Rules

1. Implement the simplest baseline before adding agent complexity.
2. Ground truth must never be accessible to the application or agent.
3. Synthetic ground truth must be fixed before evaluation.
4. Operational evidence should remain deterministic.
5. RAG and agent approaches must be evaluated on the same incidents.
6. Never fabricate evaluation results.
7. Evaluate retrieval independently from RCA generation.
8. Evaluate agent behavior as well as final answers.
9. Add complexity only when evaluation provides evidence that it is useful.
10. MCP is optional and must not delay the core evaluation.

---

# Current Focus

**TR-004 — Incident Data Contract**

Goal:

Define the on-disk structure and validation rules for synthetic incidents,
operational evidence, and hidden ground truth.

The contract should establish how incident data is organized before we begin
creating the synthetic incident dataset in TR-005.

Ground truth must remain evaluation-only and must never be exposed to the
RAG pipeline or investigation agent.