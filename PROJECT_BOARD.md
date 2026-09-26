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
| Epic 5 — Evaluation Framework | 🟡 IN PROGRESS |
| Epic 6 — Comparative Experiments | ⬜ TODO |
| Epic 7 — Delivery | 🟡 IN PROGRESS |
| Epic 8 — MCP Integration | 🟣 STRETCH |
| Epic 9 — Extended Production Scope | 🔵 EXTENDED |

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
- 186 tests passing, as reported in the project handoff; not rerun for this documentation update
- Real INC-001 smoke run saved `experiments/results/INC-001-agent.json`
- The smoke run stopped with `duplicate_selection` after three tool calls
- That run did not reach deployment/code-change evidence, leaving a broader RCA for later trace evaluation and failure analysis

These checks demonstrate execution and persistence behavior. They do not establish measured RCA accuracy or agent superiority.

### TR-026A — Agent CLI / Demo Harness

Completed:
- Added `scripts/investigate.py`
- CLI entry point for a complete TraceRoot investigation
- Required `--incident-id`
- Configurable `--max-tool-calls`
- Existing incident loader and agent experiment runner reused
- Human-readable hypotheses and tool trace
- Stop reason/reasoning output
- Final RCA, explanation, confidence, and evidence citations
- Persisted trace path
- Missing incident handled cleanly
- CLI tests
- Full validation: **194 tests passing**

Smoke test:
- Incident: `INC-001`
- Tool budget: `4`
- metrics / checkout-service
- logs / checkout-service
- logs / payment-service
- metrics / database-service
- Terminated with `tool_budget_exhausted`
- Final RCA identified checkout-service database connection contention/saturation
- The limited tool budget did not reach deployment/code-change evidence

Evaluation note:
- The result identified the affected root-cause area but did not identify the exact `100 → 20` connection-pool configuration regression
- This is a useful case for later failure analysis and trace evaluation

---

# Epic 5 — Evaluation Framework

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-027 | DeepEval Setup | 1h | ✅ DONE |
| TR-028 | Root-Cause Accuracy Evaluator | 1h | ✅ DONE |
| TR-029 | Evidence Precision & Recall | 1h | ✅ DONE |
| TR-030 | DeepEval Faithfulness | 1h | ✅ DONE |
| TR-031 | DeepEval Relevancy | 1h | ✅ DONE |
| TR-032 | Agent Trace Evaluator | 1.5h | ✅ DONE |
| TR-033 | Efficiency, Cost & Latency Instrumentation | 1.5h | ✅ DONE |
| TR-034 | Unified Evaluation Runner | 2h | ✅ DONE |

### TR-027 — DeepEval Setup

Completed:
- Added DeepEval dependency
- Added reusable `LLMTestCase` construction helper
- Input, actual output, and optional expected output mapped correctly
- Unit tests added
- DeepEval kept out of production runtime paths
- Real `AnswerRelevancyMetric` smoke test executed successfully

Smoke test:

```text
Score: 1.0
```

### TR-028 — Root-Cause Accuracy Evaluator

Completed:
- Semantic root-cause correctness evaluation
- Uses evaluator-only `GroundTruth`
- DeepEval `GEval`
- Compares generated root cause against expected root cause semantically
- Uses public DeepEval `.measure()` API
- Returns TraceRoot `MetricResult` with score, pass/fail, and reason
- Full project validation: **203 tests passing**

Smoke test:

```text
Score: 1.0
Passed: True
```

Important:
- This validates the evaluator behavior, not overall TraceRoot accuracy

### TR-029 — Evidence Precision & Recall

Completed:
- Deterministic operational-evidence precision and recall
- Uses generated `RCAResult.evidence_ids` and evaluator-only `GroundTruth.supporting_evidence_ids`
- Set semantics remove duplicate IDs
- Empty predictions/relevant sets handled
- No LLM required
- Full project validation: **209 tests passing**

Smoke test:

```text
Precision: 1.0
Recall: 1.0
```

Important:
- Smoke used a manually complete INC-001 evidence set
- It validates the metric, not agent performance
- Supporting-evidence lists must be audited and frozen before final reporting

### TR-030 — DeepEval Faithfulness

Completed:
- Added DeepEval `FaithfulnessMetric`
- Evaluates whether RCA claims are supported by the context actually available to the approach
- No hidden ground truth used
- RAG context = retrieved knowledge
- Agent context = gathered operational evidence
- Uses `gpt-5.4-mini` evaluator
- Score, pass/fail, and reason mapped to `MetricResult`
- Unit tests use the existing `@patch(...)` annotation style
- Full project validation: **214 tests passing**

Smoke test:

```text
Score: 1.0
Passed: True
Reason: The actual output aligned with the supplied retrieval context with no contradiction.
```

### TR-031 — DeepEval Relevancy

Completed:
- Added DeepEval `AnswerRelevancyMetric`
- Evaluates whether the generated RCA directly addresses the incident question
- No ground truth or retrieval context required
- Uses `gpt-5.4-mini` evaluator
- Score, pass/fail, and reason mapped to `MetricResult`
- Unit tests use the existing `@patch(...)` annotation style
- Full project validation: **218 tests passing**

Smoke test:

```text
Score: 1.0
Passed: True
Reason: The response directly addressed the checkout incident question with no irrelevant statements.
```

### TR-032 — Agent Trace Evaluator

Completed:
- Added deterministic agent-trace evaluation
- Tool Efficiency = unique `(tool_name, service)` selections / total tool calls
- Empty Tool Rate = tool calls with no evidence IDs / total tool calls
- Evidence Coverage = evaluator-known supporting evidence gathered / total supporting evidence
- Stop Quality based on investigation stop reason
- Trace-quality evaluation kept independent from final RCA correctness
- Uses evaluator-only `GroundTruth` only for supporting-evidence coverage
- Full project validation: **225 tests passing**

Smoke test on persisted INC-001 agent run:

```text
Tool Efficiency: 1.0 — Passed
Empty Tool Rate: 0.25 — Passed
Evidence Coverage: 0.8 — Passed
Stop Quality: 0.0 — Failed
Stop reason: tool_budget_exhausted
```

Interpretation:
- The investigation avoided duplicate tool/service selections
- One of four tool calls returned no evidence
- Four of five evaluator-known supporting evidence IDs were gathered
- The investigation exhausted its tool budget before reaching the remaining evidence
- This result is retained for later comparative and failure analysis rather than hidden

### TR-033 — Efficiency, Cost & Latency Instrumentation

Completed:
- Added deterministic LLM cost calculation from token counts and supplied per-million-token prices
- Added `ExecutionMetrics` support for:
  - latency
  - LLM calls
  - tool calls
  - input tokens
  - output tokens
  - total tokens
  - estimated cost
  - investigation steps
- Added non-negative Pydantic validation for execution metrics
- Pricing is passed into the cost calculator rather than hard-coded
- Unavailable runtime token/cost values are not fabricated
- Full project validation: **232 tests passing**

Smoke test:

```text
Latency ms: 850.0
LLM calls: 3
Tool calls: 4
Input tokens: 1200
Output tokens: 300
Total tokens: 1500
Estimated cost USD: 0.0024
```

Important:
- This smoke validates the calculation and execution-metrics contract
- Real comparative token/cost reporting still depends on wiring actual runtime usage into experiment execution
- Model pricing assumptions must be documented when final TR-036 results are produced

### TR-034 — Unified Evaluation Runner

Completed:
- Added one evaluation workflow for persisted RAG experiment records
- Added one evaluation workflow for persisted Agent experiment records
- RAG evaluation runs:
  - Root-Cause Accuracy
  - Faithfulness
  - Relevancy
- Agent evaluation runs:
  - Root-Cause Accuracy
  - Evidence Precision
  - Evidence Recall
  - Faithfulness
  - Relevancy
  - Tool Efficiency
  - Empty Tool Rate
  - Evidence Coverage
  - Stop Quality
- RAG faithfulness receives the actual retrieved context explicitly because `BaselineExperimentRecord` stores provenance rather than full chunk text
- Agent faithfulness context is reconstructed from persisted `tool_history[*].observations`
- Ground truth is passed only to evaluators that require it
- Unified results are returned as `EvaluationResult`
- Existing execution latency and tool/investigation-step counts are preserved
- Full project validation: **239 tests passing**

Smoke test:

```text
RAG
Root Cause Accuracy 1.0 True
Faithfulness 1.0 True
Relevancy 1.0 True

AGENT
Root Cause Accuracy 1.0 True
Evidence Precision 1.0 True
Evidence Recall 1.0 True
Faithfulness 1.0 True
Relevancy 1.0 True
Tool Efficiency 1.0 True
Empty Tool Rate 0.0 True
Evidence Coverage 1.0 True
Stop Quality 1.0 True
```

Important:
- The smoke validates unified evaluator orchestration
- It is not the final RAG-vs-Agent comparative experiment
- Final measured comparison remains TR-036 on the frozen dataset

---

# Epic 6 — Comparative Experiments

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-035 | Expand & Freeze Final Evaluation Dataset using OpenTelemetry Demo scenarios | 3h | ⬜ TODO |
| TR-036 | Run RAG vs Agent Evaluation | 1h | ⬜ TODO |
| TR-037 | Failure & Error Analysis | 1h | ⬜ TODO |
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
- Ground-truth relevant evidence sets audited before evidence precision/recall reporting
- No real company/customer data or PII included

### TR-036 — Run RAG vs Agent Evaluation

Goal:
- Run the mandatory RAG-vs-Agent comparative experiment on the same frozen incidents

Report per incident:
- RCA accuracy
- faithfulness
- relevancy
- evidence precision/recall where applicable
- trace quality
- latency
- LLM/tool calls
- token usage where available
- estimated cost

Requirements:
- comparable inputs and documented model configuration
- no manual correction of outputs
- raw outputs persisted before scoring
- failed runs preserved
- measured results only

### TR-037 — Failure & Error Analysis

Analyze:
- incorrect/partial/broad-but-incomplete RCA
- unsupported RCA
- retrieval/evidence failures
- premature stop / duplicate selection / empty tools / budget exhaustion
- missing telemetry / distractor sensitivity
- malformed LLM output / evaluator-runtime failure
- cost and latency outliers

Classify where possible as model reasoning, retrieval, tool/evidence, insufficient data, guardrail, or evaluator/runtime failure.

### TR-038 — Evidence-Driven Improvement

Goal:
- Make only improvements justified by measured failure modes
- Keep the frozen evaluation dataset unchanged
- Avoid architecture changes without evidence

### TR-039 — Re-evaluate & Compare

Goal:
- Re-run the improved system against the same frozen dataset
- Preserve before/after results
- Report regressions as well as improvements
- Never fabricate improvement

---

# Epic 7 — Delivery

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-040 | README + Architecture + Capstone Report + Results | 2.5h | 🟡 IN PROGRESS |
| TR-041 | Demo Video / Public Demo | 1h | ⬜ TODO |

### TR-040 — README + Architecture + Capstone Report + Results

Current deliverables:
- [README](README.md)
- [Architecture guide](docs/ARCHITECTURE.md)
- `docs/CAPSTONE_REPORT.md` — pending

`docs/ARCHITECTURE.md` must explicitly document:
- high-level, RAG, and agent architecture
- investigation state and deterministic tool layer
- evidence grounding and ground-truth isolation
- persistence and evaluation architecture
- architecture trade-offs
- synchronous loop decision
- chunking strategy, chunk size/overlap, and rationale
- embedding/Qdrant choices
- operational tool choices and guardrails
- file-backed evaluation surface vs future production adapters

`docs/CAPSTONE_REPORT.md` must map directly to the official rubric:

1. **Problem Definition** — scoping, clarity, research question, success criteria, limitations
2. **Data Processing** — sources, normalization, evidence IDs, PII handling, guardrails, provenance, ground-truth isolation
3. **System Design** — architecture, flows, tools, chunking, persistence, trade-offs
4. **Evals** — task-specific metrics, error/failure handling, cost, latency, final RAG-vs-Agent results

Remaining:
- Create `CAPSTONE_REPORT.md`
- Finalize architecture against the rubric
- Add measured comparative results and failure/error analysis
- Document frozen dataset/provenance and cost/latency results
- Final consistency pass across README, architecture, and report

Keep TR-040 in progress until real evaluation results are included.

### TR-041 — Demo Video / Public Demo

Submission requires:
- public project code URL
- either a hosted application or a demo video

Preferred path:

```text
Public GitHub Repository
        +
3–5 Minute Demo Video
```

Demo should show:
1. problem and research question
2. architecture
3. RAG baseline
4. agent investigation
5. hypotheses/tool calls/evidence
6. final RCA
7. comparative evaluation results
8. one meaningful failure-analysis insight
9. quality vs cost/latency trade-off

Final submission checklist:
- code URL
- demo URL
- system design document URL
- problem definition / data processing / evaluation criteria document URL
- optional additional context

---

# Epic 8 — Optional MCP Integration

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-042 | MCP Evidence Server | 2h | 🟣 STRETCH |
| TR-043 | LangGraph ↔ MCP Integration | 1h | 🟣 STRETCH |

MCP must not delay the core experiment.

---

# Epic 9 — Extended Scope / Productionization

| Ticket | Description | Estimate | Status |
|---|---|---:|---|
| TR-044 | Live Incident Intake | 1.5h | 🔵 EXTENDED |
| TR-045 | Live Evidence Integrations | 4h+ | 🔵 EXTENDED |
| TR-046 | Simple Investigation UI | 2h | 🔵 EXTENDED |

This epic is outside the capstone critical path. The current file-backed incident and evidence sources remain the reproducible evaluation environment.

### TR-044 — Live Incident Intake

Goal:

Allow TraceRoot to start an investigation from newly received incident information instead of requiring a pre-created incident fixture.

Potential intake channels:
- CLI
- REST API
- Manual UI form
- PagerDuty / Opsgenie
- Slack / Teams

Minimum incident input:
- title
- description
- incident start time
- suspected or affected services when known

Target flow:

```text
Alert / Engineer / Incident Platform
              ↓
        Incident Intake
              ↓
        TraceRoot Incident
              ↓
     Agentic Investigation
```

The runtime-generated incident should use the same `Incident` domain contract as evaluation incidents.

### TR-045 — Live Evidence Integrations

Goal:

Replace or complement the current file-backed evidence providers with adapters to live operational systems while preserving the existing agent/tool contracts.

Potential integrations:
- Logs → Splunk / CloudWatch / Elasticsearch
- Metrics → Prometheus / Datadog / Grafana-compatible sources
- Traces → OpenTelemetry
- Deployments → Kubernetes / Argo CD / CI/CD systems
- Code changes → GitHub / GitLab

Architecture principle:

```text
Evaluation Mode
Frozen JSON evidence
        ↓
Existing TraceRoot tools

Production Mode
Live observability / deployment / Git APIs
        ↓
Evidence adapters
        ↓
Same TraceRoot investigation workflow
```

The investigation agent should not need to know whether evidence comes from frozen fixtures or live adapters.

### TR-046 — Simple Investigation UI

Goal:

Provide a lightweight interface for starting and observing an investigation.

Minimum UI capabilities:
- Start a new investigation from title, description, start time, and optional suspected service
- Select an existing evaluation incident for demos
- Display generated hypotheses and their statuses
- Display tool calls and selected services
- Display gathered evidence
- Display stop reason
- Display final RCA, confidence, and cited evidence
- Display or link to the persisted investigation trace

Suggested first implementation:
- Streamlit for a fast prototype

Possible later architecture:
- FastAPI backend
- React frontend

The UI is a presentation and intake layer only; core investigation logic must remain in the existing TraceRoot modules.

---

# Kanban

## 🟡 In Progress

- TR-040 — README + Architecture + Capstone Report + Results

## ⬜ Next Up

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
- TR-027 — DeepEval Setup
- TR-028 — Root-Cause Accuracy Evaluator
- TR-029 — Evidence Precision & Recall
- TR-030 — DeepEval Faithfulness
- TR-031 — DeepEval Relevancy
- TR-032 — Agent Trace Evaluator
- TR-033 — Efficiency, Cost & Latency Instrumentation
- TR-034 — Unified Evaluation Runner

## 🟣 Stretch

- TR-042 — MCP Evidence Server
- TR-043 — LangGraph ↔ MCP Integration

## 🔵 Extended Scope

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
11. File-backed incident evidence is the reproducible evaluation surface; live incident intake, production evidence integrations, and UI work are extended scope and must not delay comparative evaluation.
12. Final documentation must explicitly cover Problem Definition, Data Processing, System Design, and Evals.
13. Cost and latency must be measured and reported, not merely discussed.
14. Chunking strategy and operational tool choices must be documented in the system design document.
15. PII handling and data-source provenance must be explicitly documented.
16. Evaluation/runtime errors and system failures must be recorded and analyzed rather than hidden.
17. Final submission must expose public code plus either a hosted application or demo video.
18. No comparative-superiority claim should be made before measured TR-036 results exist.

---

# Current Focus

**TR-035 — Expand & Freeze Final Evaluation Dataset using OpenTelemetry Demo scenarios**, alongside progressive work on TR-040 documentation.

Current state:
- TR-001 through TR-034 complete
- **239 tests passing**
- Knowledge-only RAG and agentic investigation complete
- Agent CLI/demo harness complete
- DeepEval setup, RCA accuracy, evidence precision/recall, faithfulness, relevancy, and agent-trace evaluators complete
- Efficiency/cost/latency metric contracts complete
- Unified RAG/Agent evaluation runner complete
- Three current synthetic incidents
- OpenTelemetry-derived final dataset expansion pending
- Comparative RAG-vs-Agent evaluation pending
- README and architecture drafts exist
- `CAPSTONE_REPORT.md` pending
- No measured agent-superiority claim has been made

Evaluation progress:

```text
Retrieval Recall@K             ✅
DeepEval Setup                 ✅
Root-Cause Accuracy            ✅
Evidence Precision / Recall    ✅
Faithfulness                   ✅
Relevancy                      ✅
Agent Trace Quality            ✅
Cost / Latency / Efficiency    ✅
Unified Evaluation Runner      ✅
RAG vs Agent Experiment        ⬜
Failure / Error Analysis       ⬜
```

Next:
1. Verify, expand, audit, and freeze the final six-incident dataset (TR-035).
2. Run RAG vs Agent comparative experiments (TR-036).
3. Perform failure/error analysis (TR-037).
4. Make evidence-driven improvements and re-evaluate only if time permits (TR-038–TR-039).
5. Complete `CAPSTONE_REPORT.md`, architecture/results, and README (TR-040).
6. Record and publish the demo video / public demo URL (TR-041).

Known items to address during evaluation:
- Hypothesis verification does not enforce evidence citations and matches by description rather than a stable hypothesis ID
- Hypothesis-assessment reasoning is not retained in hypothesis state
- Recall@5 has limited discrimination on the small knowledge corpus
- Baseline prompts use title/description; agent prompts include richer incident context, notably `suspected_services`
- Guardrail stops and valid evidence IDs alone do not establish a correct or complete RCA
- Ground-truth supporting-evidence sets must be audited before final precision/recall reporting
- Real token/cost reporting still requires actual runtime usage capture rather than synthetic smoke-test values

Extended scope after the core capstone:
- TR-044 — Live Incident Intake
- TR-045 — Live Evidence Integrations
- TR-046 — Simple Investigation UI
