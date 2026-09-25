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
| Epic 3 — Operational Evidence Tools | ✅ DONE |
| Epic 4 — Agentic Investigation | ✅ DONE |
| Epic 5 — Evaluation Framework | ⬜ TODO |
| Epic 6 — Comparative Experiments | ⬜ TODO |
| Epic 7 — Delivery | 🟡 IN PROGRESS |
| Epic 8 — MCP Integration | 🟣 STRETCH |
| Epic 9 — Extended Scope / Productionization | 🔵 EXTENDED |

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

Evaluation note:
- Current corpus produces only a small number of chunks
- Recall@5 is therefore not sufficiently discriminative for final evaluation
- Final reporting should emphasize Recall@1 and Recall@3
- Recall@5 can remain as a completeness metric

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
| TR-019 | Tool Interface + Tests | 1h | ✅ DONE |

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

### TR-019 — Tool Interface + Tests

Completed:
- Unified `ToolName` enum
- Unified `execute_tool()` dispatcher
- Logs dispatch
- Metrics dispatch
- Deployments dispatch
- Code-changes dispatch
- `incident_id` propagation
- `service` propagation
- Underlying typed results returned unchanged
- Unknown tool rejection
- No ground-truth access
- No LLM involvement
- Real INC-001 unified logs query manually verified
- 117 tests passing across project at ticket completion

---

# Epic 4 — Agentic Investigation

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-020 | LangGraph Investigation State | 1h | ✅ DONE |
| TR-021 | Hypothesis Generation | 1h | ✅ DONE |
| TR-022 | Tool Selection & Investigation Loop | 2h | ✅ DONE |
| TR-023 | Hypothesis Verification/Rejection | 1h | ✅ DONE |
| TR-024 | Investigation Guardrails | 1h | ✅ DONE |
| TR-025 | Evidence-Grounded RCA Generation | 1h | ✅ DONE |
| TR-026 | Investigation Trace Persistence | 45m | ✅ DONE |
| TR-026A | Agent CLI / Demo Harness | 45m | ✅ DONE |

### TR-020 — LangGraph Investigation State

Completed:
- `HypothesisStatus`
- `Hypothesis`
- `ToolCallRecord`
- `InvestigationState`
- Incident state preservation
- Hypothesis state tracking
- Operational evidence ID tracking
- Tool-call history tracking
- Optional final RCA result
- Independent mutable defaults
- Investigation-state tests

Note:
- Current implementation uses a simple synchronous Python investigation loop
- LangGraph has not been introduced because it is not required for the current experiment

### TR-021 — Hypothesis Generation

Completed:
- Structured LLM-generated incident hypotheses
- Configurable maximum hypothesis count
- Incident-only prompt context
- No operational evidence access during hypothesis generation
- No ground-truth access
- Generated hypotheses mapped to `Hypothesis`
- Initial hypothesis status defaults to `OPEN`
- Structured-output failure handling
- Mocked LLM tests

### TR-022 — Tool Selection & Investigation Loop

Completed:
- Structured `ToolSelection`
- LLM-driven operational tool selection
- Optional service filtering
- Deterministic `execute_tool()` integration
- Operational evidence gathering
- Global evidence-ID deduplication
- Per-call evidence history
- Tool observations preserved for subsequent reasoning
- Tool-selection reasoning preserved
- Configurable investigation tool-call budget
- Real INC-001 investigation flow manually verified

### TR-023 — Hypothesis Verification/Rejection

Completed:
- Structured hypothesis assessment
- `OPEN`, `SUPPORTED`, and `REJECTED` outcomes
- Incident context included in verification
- Existing hypotheses included in verification
- Gathered operational observations included in verification
- No new hypotheses created during verification
- Existing investigation state preserved
- Missing structured-output handling
- Mocked LLM verification tests
- Real INC-001 hypothesis verification manually verified

Known evaluation-phase improvement:
- Verification currently does not require evidence IDs for each assessment
- Hypothesis descriptions are currently used for matching rather than stable hypothesis IDs

### TR-024 — Investigation Guardrails

Completed:
- Investigation-wide tool-call budget
- Existing tool history counts toward remaining budget
- Explicit LLM-requested stop
- Duplicate `(tool_name, service)` prevention
- Previously attempted tool/service pairs reconstructed from history
- Two-consecutive-empty-results guardrail
- Selected service preserved in `ToolCallRecord`
- Investigation `stop_reason` tracking
- Investigation `stop_reasoning` tracking
- Single LLM client reused during investigation
- Tool-selection prompt documents available tools
- Tool-selection prompt documents duplicate-call rule
- Tool-selection prompt documents explicit stopping behavior
- Guardrail unit tests updated
- Ruff and full pytest validation passing
- Real INC-001 smoke test successfully verified

Smoke-test flow:

```text
metrics / checkout-service
        ↓
logs / checkout-service
        ↓
deployments / checkout-service
        ↓
code_changes / checkout-service
```

Smoke-test termination:

```text
tool_budget_exhausted
```

### TR-025 — Evidence-Grounded RCA Generation

Completed:
- Final RCA generation from incident context, assessed hypotheses, and gathered tool observations
- Structured output mapped to `RCAResult` and stored in `InvestigationState.final_result`
- Final cited evidence IDs checked against the gathered evidence IDs
- Unknown evidence IDs rejected
- RCA generation rejected when no evidence was gathered
- Missing structured-output handling
- Mocked LLM and prompt-boundary tests
- Implementation committed

Grounding limit:
- Evidence-ID validation establishes citation membership, not causal correctness
- The current validator does not require a nonempty final citation list when evidence was gathered
- Root-cause accuracy and evidence quality remain evaluation work

### TR-026 — Investigation Trace Persistence

Completed:
- `AgentExperimentRecord` with approach and model metadata
- `run_agent_experiment()` orchestrates hypothesis generation, investigation, verification, final RCA generation, and persistence
- Hypothesis statuses, gathered evidence IDs, tool history, and observations persisted
- Stop reason and stop reasoning persisted
- Final `RCAResult`, execution latency, and timezone-aware timestamp persisted
- JSON persistence with parent-directory creation
- Orchestration and persistence tests
- Implementation committed

Recorded validation at ticket completion:
- 186 tests passing
- Real INC-001 smoke run saved `experiments/results/INC-001-agent.json`
- The smoke run stopped with `duplicate_selection` after three tool calls
- That run did not reach deployment/code-change evidence, leaving a broader RCA for later trace evaluation and failure analysis

These checks demonstrate execution and persistence behavior. They do not establish measured RCA accuracy or agent superiority.

### TR-026A — Agent CLI / Demo Harness

Completed:
- Added `scripts/investigate.py`
- CLI entry point for running a complete TraceRoot investigation
- Required `--incident-id` argument
- Configurable `--max-tool-calls`
- Deterministic incident and output path construction
- Existing `load_incident()` reused
- Existing `run_agent_experiment()` reused
- Human-readable hypothesis output
- Human-readable investigation trace
- Stop reason and stop reasoning displayed
- Final RCA, affected service, explanation, confidence, and cited evidence displayed
- Persisted trace path displayed
- Missing incident handled with a clear CLI error
- CLI unit tests added
- Full project validation completed with **194 tests passing**

Smoke test:

```bash
uv run python scripts/investigate.py \
  --incident-id INC-001 \
  --max-tool-calls 4
```

Observed investigation:

```text
metrics / checkout-service
        ↓
logs / checkout-service
        ↓
logs / payment-service
        ↓
metrics / database-service
        ↓
no metric evidence returned
```

Termination:

```text
tool_budget_exhausted
```

The final RCA identified database connection contention/saturation in `checkout-service` as the likely cause and cited gathered log/metric evidence.

Evaluation note:
- With a four-tool budget, this run did not reach deployment or code-change evidence
- It therefore identified the operational bottleneck but not the exact configuration regression
- This is a useful scenario for later agent trace, efficiency, and failure analysis

Architectural boundary:
- The current CLI uses frozen incident fixtures for reproducible evaluation
- Production incident intake and live observability integrations are explicitly deferred to Extended Scope

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
| TR-035 | Expand & Freeze Final Evaluation Dataset using OpenTelemetry Demo scenarios | 3h | ⬜ TODO |
| TR-036 | Run RAG vs Agent Evaluation | 1h | ⬜ TODO |
| TR-037 | Failure Analysis | 1h | ⬜ TODO |
| TR-038 | Evidence-Driven Improvement | 1.5h | ⬜ TODO |
| TR-039 | Re-evaluate & Compare | 1h | ⬜ TODO |

### TR-035 — Expand & Freeze Final Evaluation Dataset

Goal:

Combine the existing controlled synthetic incidents with realistic failure scenarios derived from the OpenTelemetry Demo / Astronomy Shop, then freeze the dataset for comparative evaluation.

Retain the current baseline cases:
- INC-001 — checkout database connection-pool regression
- INC-002 — payment-service currency serialization regression
- INC-003 — order-worker backlog caused by inventory timeout

Planned additions, subject to scenario verification and evidence review:
- INC-004 — Ad service failure: downstream/service dependency failure
- INC-005 — Email service memory leak: progressive resource degradation
- INC-006 — Cart service failure: functional downstream-service failure

The additions are not yet present. Use OpenTelemetry Demo as a scenario source and evidence generator, and document whether each resulting fixture is captured, adapted, or synthesized.

Preserve the existing data contract:

```text
data/incidents/INC-00X/
├── incident.json
├── logs.jsonl
├── metrics.json
├── deployments.json
└── changes.json

data/ground_truth/INC-00X.json  # evaluator-only
```

Acceptance criteria:
- Stable evidence IDs, causal evidence, and plausible distractors
- Sufficient evidence for a reasonable investigator to identify the root cause
- Scenario provenance documented for every new incident
- Dataset consistency and ground-truth evidence references validated offline
- Ground truth fixed before evaluation and excluded from RAG/agent runtime inputs
- No requirement for OpenTelemetry Demo to be running during evaluation
- The exact same frozen incident set used for both approaches
- Incident-field parity, including `suspected_services`, resolved or explicitly controlled before TR-036
- Final dataset reviewed and frozen before comparative results are reported

---

# Epic 7 — Delivery

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-040 | README + Architecture + Results | 2h | 🟡 IN PROGRESS |
| TR-041 | 3-Minute Demo | 1h | ⬜ TODO |

### TR-040 — README + Architecture + Results

Drafted for review:
- [Starter README](README.md) reflecting the implementation through TR-026A
- [Architecture guide](docs/ARCHITECTURE.md) with simplified architecture, Mermaid flow diagrams, and a three-minute demo explanation
- Setup/run examples, current limitations, and experimental boundaries
- CLI investigation entry point documented

Remaining:
- Review the documentation drafts
- Add measured comparative results and failure analysis after evaluation
- Refresh the final documentation with the evaluated configuration and frozen dataset

Keep TR-040 in progress until results are available and the delivery documentation is finalized. The demo outline does not complete TR-041.

---

# Epic 8 — Optional MCP Integration

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-042 | MCP Evidence Server | 2h | 🟣 STRETCH |
| TR-043 | LangGraph ↔ MCP Integration | 1h | 🟣 STRETCH |

MCP must not delay the core experiment.

---

# Epic 9 — Extended Scope / Productionization

These items are intentionally outside the core capstone evaluation scope and must not delay TR-027 through TR-041.

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-044 | Live Incident Intake | TBD | 🔵 EXTENDED |
| TR-045 | Live Evidence Integrations | TBD | 🔵 EXTENDED |
| TR-046 | Simple Investigation UI | TBD | 🔵 EXTENDED |

### TR-044 — Live Incident Intake

Goal:

Allow TraceRoot investigations to begin from newly received incident information rather than requiring a pre-created evaluation incident directory.

Potential inputs:
- CLI
- REST API
- PagerDuty / Opsgenie
- Slack / Teams
- Manual UI form

Initial incident information:
- title
- description
- start time
- suspected or affected services

Conceptual flow:

```text
Incident Alert / Engineer
          ↓
     Incident Intake
          ↓
        Incident
          ↓
TraceRoot Investigation
```

This separates production incident intake from the frozen evaluation fixtures.

### TR-045 — Live Evidence Integrations

Goal:

Replace file-backed operational evidence adapters with production-system integrations while preserving the same investigation workflow.

Potential integrations:

```text
Logs
→ Splunk / CloudWatch / Elasticsearch

Metrics
→ Prometheus / Datadog / Grafana

Deployments
→ Kubernetes / ArgoCD / CI/CD

Code Changes
→ GitHub / GitLab

Traces
→ OpenTelemetry
```

The agent investigation logic should remain largely unchanged. The evidence adapters behind the tool interface change.

Production flow:

```text
Live Incident
     ↓
TraceRoot Agent
     ↓
Operational Tool Interface
     ↓
Logs / Metrics / Deployments / Git / Traces
     ↓
Evidence-Grounded RCA
```

### TR-046 — Simple Investigation UI

Goal:

Provide a lightweight human-facing investigation interface.

Initial UI capabilities:
- Start a new incident investigation
- Select an existing evaluation incident
- View generated hypotheses
- View tool calls
- View gathered evidence
- View hypothesis status
- View investigation stop reason
- View final RCA
- View confidence
- View cited evidence
- View persisted investigation trace

Suggested first implementation:
- Streamlit

Possible later architecture:
- FastAPI backend
- React frontend

This UI is an extended-scope usability layer and is not required for the core comparative experiment.

---

# Kanban

## 🟡 In Progress

- TR-040 — README + Architecture + Results (documentation drafted; review and results pending)

## ⬜ Next Up

- TR-027 — DeepEval Setup
- TR-028 — Root-Cause Accuracy Evaluator
- TR-029 — Evidence Precision & Recall
- TR-035 — Expand & Freeze Final Evaluation Dataset using OpenTelemetry Demo scenarios

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
- TR-019 — Tool Interface + Tests
- TR-020 — LangGraph Investigation State
- TR-021 — Hypothesis Generation
- TR-022 — Tool Selection & Investigation Loop
- TR-023 — Hypothesis Verification/Rejection
- TR-024 — Investigation Guardrails
- TR-025 — Evidence-Grounded RCA Generation
- TR-026 — Investigation Trace Persistence
- TR-026A — Agent CLI / Demo Harness

## 🟣 Stretch

- TR-042 — MCP Evidence Server
- TR-043 — LangGraph ↔ MCP Integration

## 🔵 Extended

- TR-044 — Live Incident Intake
- TR-045 — Live Evidence Integrations
- TR-046 — Simple Investigation UI

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
11. Frozen incident files are the reproducible evaluation data surface, not the intended production incident-ingestion mechanism.
12. Live integrations and UI work are extended scope and must not delay comparative evaluation or submission.

---

# Current Focus

**TR-027 — DeepEval Setup**, alongside review of the TR-040 documentation drafts.

Current state:
- TR-001 through TR-026A complete
- Knowledge-only RAG and agentic investigation execute and persist outputs
- Agent investigation can be started through `scripts/investigate.py`
- Three synthetic incidents and five engineering knowledge documents available
- Retrieval benchmark, Recall@K evaluator, and evaluation contracts implemented
- Full project validation currently at **194 tests passing**
- README and architecture documentation are being updated
- Final RCA evaluation, expanded dataset, comparative experiments, and failure analysis pending
- No measured RCA accuracy or RAG-versus-agent improvement claimed

Next:
1. Set up DeepEval within this repository and implement the remaining evaluation metrics and unified runner (TR-027–TR-034).
2. Verify the three proposed OpenTelemetry scenarios, normalize and review their evidence, and freeze the final dataset (TR-035).
3. Resolve incident-input parity, run both approaches on the frozen incidents, and analyze correctness, evidence quality, agent behavior, and efficiency (TR-036–TR-037).
4. Make evidence-driven improvements, re-evaluate, and complete results documentation and the demo (TR-038–TR-041).

Known items to address during evaluation:
- Hypothesis verification does not enforce evidence citations and matches by description rather than a stable hypothesis ID
- Hypothesis-assessment reasoning is not retained in hypothesis state
- Recall@5 has limited discrimination on the small knowledge corpus
- Baseline prompts use title/description; agent prompts include richer incident context, notably `suspected_services`
- Guardrail stops and valid evidence IDs alone do not establish a correct or complete RCA
- TR-026A demonstrated that a limited tool budget can identify an operational bottleneck without reaching the deeper deployment/code-change cause