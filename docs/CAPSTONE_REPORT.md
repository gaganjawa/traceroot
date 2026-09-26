# TraceRoot Capstone Report

## 1. Problem Definition

Software production incident root-cause analysis (RCA) is often slow because useful evidence is spread across logs, metrics, deployments, code changes, and engineering knowledge. Knowledge-only retrieval-augmented generation (RAG) can retrieve general documentation but cannot inspect incident-specific operational evidence. TraceRoot compares this baseline with an Agent that actively gathers operational evidence.

> Can agentic evidence gathering improve root-cause identification and evidence grounding compared with knowledge-only RAG for software production incidents?

The first release is a controlled, reproducible experiment using file-backed evidence and a frozen six-incident dataset. It includes no live production telemetry or real company/customer data. Success is assessed through RCA quality, evidence grounding, investigation behavior, and latency/cost trade-offs; a higher accuracy score alone is insufficient to establish practical value.

## 2. Data Processing

`INC-001` to `INC-003` are controlled synthetic incidents covering a checkout database connection-pool regression, payment currency serialization regression, and order backlog caused by inventory timeouts. `INC-004` to `INC-006` are synthetic/adapted scenarios based on OpenTelemetry Demo / Astronomy Shop failure modes: intermittent ad retrieval failure, email memory degradation, and EmptyCart failure. These are not captured production traces. OpenTelemetry Demo supplies scenario provenance, not a runtime dependency.

The normalized local evidence contract is:

```text
data/incidents/INC-00X/
├── incident.json
├── logs.jsonl
├── metrics.json
├── deployments.json
└── changes.json

data/ground_truth/INC-00X.json  # evaluator-only
```

Operational entries carry stable evidence IDs and include plausible distractors. Separate ground-truth files hold expected causes and supporting-evidence labels for evaluation. Labels distinguish gathered-label coverage from final cited-label coverage; an unlabeled observation is not necessarily irrelevant. The dataset and labels were frozen before comparative evaluation. Provenance and synthesized artifacts are documented in [docs/DATASET_PROVENANCE.md](DATASET_PROVENANCE.md). There is no PII or real company/customer data.

Ground truth is evaluator-only and never available to runtime RAG or Agent flows. Runtime `IncidentDataset` excludes it; runtime loaders/tools do not load ground-truth files. Expected causes and supporting-evidence labels stay out of prompts, observations, and the knowledge index. This is an application data-access contract, not an operating-system security boundary.

Input parity remains a limitation: RAG retrieval uses incident title and description, while the Agent receives richer incident context, including `suspected_services` when present. Results must be interpreted with this difference intact.

## 3. System Design

### 3.1 Knowledge-only RAG baseline

Engineering knowledge documents in `data/knowledge/` use Markdown with YAML metadata. Word-based chunking defaults to **600 words with 100 words of overlap**, preserving source metadata and assigning deterministic `<source>::<chunk_index>` chunk IDs. `text-embedding-3-small` produces 1536-dimensional vectors, indexed in Qdrant with cosine similarity and deterministic UUID5 point IDs derived from chunk IDs.

The final comparison uses `top_k=3`, with incident title/description as the retrieval query. Retrieved knowledge supports a final structured `RCAResult`. Chunk/source/similarity provenance is persisted separately from operational `evidence_ids`, which remain empty for RAG. The baseline does not inspect logs, metrics, deployments, or code changes.

### 3.2 Agentic investigation

An `Incident` supplies context for initial LLM hypothesis generation. `InvestigationState` retains the incident, hypotheses, gathered evidence IDs, tool history, stop information, and final result. The LLM selects a tool and optional service filter; deterministic tools retrieve local **logs, metrics, deployments, and code changes**. Observations and per-call IDs enter tool history, while gathered IDs are deduplicated globally.

After investigation, hypothesis verification classifies existing hypotheses as `OPEN`, `SUPPORTED`, or `REJECTED`. Verification is not interleaved after every call. Final RCA generation uses the incident, assessed hypotheses, and observations. Evidence-ID membership validation rejects citations outside the gathered set; generation fails if no evidence was gathered. Trace persistence records hypotheses, observations, executed tools/services, evidence IDs, final RCA, stop information, and execution measurements.

Guardrails stop investigation at the maximum tool-call budget (six in the comparison), an explicit model stop, a duplicate executed tool/service pair, or two consecutive empty results. `stop_reason` and `stop_reasoning` preserve termination information.

TR-038 focused on investigation selection. Its prompt treats `suspected_services` as leads rather than guaranteed causes, encourages broadening after empty targeted searches, discourages repeated/overlapping exploration, and prefers evidence that distinguishes hypotheses. A deterministic guardrail applies when the previous targeted call returned no evidence and the next selection targets the same service: the selected tool uses `service=None`. Duplicate detection checks that actual execution pair before execution, and `ToolCallRecord` stores the actual executed service. This conditional guardrail does not always fire.

### 3.3 Architectural trade-offs

A synchronous Python loop replaces the originally contemplated LangGraph orchestration: the bounded, simple investigation flow did not require graph orchestration for this experiment. Deterministic tools improve reproducibility, and file-backed evidence avoids external-system dependencies. Qdrant supports semantic knowledge retrieval with provenance. Separate RAG and Agent evidence paths directly support the research question, while intentionally providing different evidence access.

MCP remains optional stretch work. Future adapters could connect logs from Splunk / CloudWatch / Elasticsearch; metrics from Prometheus / Datadog / Grafana-compatible sources; traces from OpenTelemetry; deployments from Kubernetes / Argo CD / CI/CD; and code changes from GitHub / GitLab. Adapters should preserve existing tool contracts. These live integrations are **not part of the current release**.

## 4. Evaluation Design

Raw outputs are persisted before scoring, with no manual correction. The comparison uses `gpt-5.4-mini`, RAG `top_k=3`, and an Agent budget of six tool calls. Ground truth is loaded for evaluation and passed only to evaluators that require it.

| Metrics | Approach | Meaning and implementation |
|---|---|---|
| Root Cause Accuracy | Both | LLM-based semantic comparison against the expected cause using DeepEval GEval. |
| Faithfulness | Both | DeepEval assessment against context actually available: retrieved knowledge for RAG, gathered observations for Agent. |
| Relevancy | Both | DeepEval assessment of whether the RCA addresses the incident question. |
| Evidence Precision / Evidence Recall | Agent | Fractions of cited IDs that are labeled supporting evidence / supporting IDs that are cited. |
| Tool Efficiency | Agent | Unique executed tool/service pairs divided by executed calls. |
| Empty Tool Rate | Agent | Fraction of executed calls returning no evidence. |
| Evidence Coverage | Agent | Fraction of labeled supporting evidence gathered. |
| Stop Quality | Agent | Score assigned from the recorded termination category. |

Evidence and trace metrics are deterministic for a saved trace and ground truth. Tool Efficiency does not measure information gain, and Stop Quality does not prove investigation completeness. Faithfulness and Relevancy do not require ground truth and do not establish causal correctness.

Execution records capture latency, LLM calls, tool calls, investigation steps, input tokens, output tokens, total tokens, and estimated runtime cost. Runtime cost covers instrumented generation/investigation calls; evaluator/judge cost is separate when absent from execution metrics. These values are not an all-in evaluation invoice.

`experiments/comparison/` holds the initial TR-036 run; `experiments/comparison-post-tr038/` holds the re-evaluation. Each contains `raw/`, `evaluations/`, and `summary.json`. The saved artifacts and TR-037/TR-039 reports establish measured findings; some comparative ticket statuses in `PROJECT_BOARD.md` remain stale.

## 5. Initial Comparative Results

The TR-036 [summary](../experiments/comparison/summary.json) and failure analysis report the following six-incident aggregates:

| Measure | RAG | Agent |
|---|---:|---:|
| Mean RCA accuracy | 0.476934 | 0.771282 |
| Mean latency | 3178.51 ms | 15634.02 ms |
| Mean runtime cost | $0.001581375 | $0.011635625 |
| Total runtime cost | $0.00948825 | $0.06981375 |

The Agent scored higher on mean RCA accuracy in this single six-incident run, requiring approximately 4.92 times the latency and 7.36 times the runtime cost. This is a measured experimental result, not proof of universal superiority. Operational evidence access intentionally differs between approaches, and the title/description versus richer Agent input limitation further constrains interpretation.

## 6. Failure Analysis

[TR-037](TR037_FAILURE_ANALYSIS.md) distinguishes failure to gather evidence from failure to cite or interpret evidence already gathered.

| Finding | Examples and classification |
|---|---|
| Hypothesis/service anchoring and incomplete gathering | INC-002 stayed on checkout-service and gathered no labeled payment evidence; INC-001 missed the initiating configuration change. Model reasoning/planning and tool/evidence selection. |
| Empty-result stopping, duplicate selection, budget exhaustion | INC-001/002 stopped after consecutive empty calls; INC-003/004/005 on duplicate selection; INC-006 exhausted its budget. Model planning interacting with guardrails. |
| Redundant citations and overlapping exploration | INC-003/004 cited broadly; all-service log sweeps in INC-004/006 repeated observations. Model citation selection and tool/evidence planning; label scope also affects precision. |
| Omitted supporting evidence | INC-006 used gathered GetCart/AddItem metrics in its explanation but omitted their IDs from final citations. Final synthesis/citation selection. |
| RAG retrieval limitations | General documentation often supported broad diagnoses or wrong localization; INC-003 was a successful runbook match. Retrieval and knowledge-only access limitations; better available chunks were not established. |
| Unresolved causal triggers | INC-004/005 observations supported failure symptoms without exposing exact `adFailure` activation or `emailMemoryLeak` body padding. Insufficient evidence/data relative to label specificity, not demonstrated disregard of decisive evidence. |

Three findings are **evaluation/data-label concerns, not confirmed implementation bugs**: INC-003 has possible unlabeled corroborating evidence; INC-004 has a scoring-severity inconsistency between similarly incomplete answers; and INC-002's wrong-service diagnosis still received a substantial RCA score (0.7000). These constrain evaluator/runtime interpretation without proving broken metric arithmetic or invalid ground truth. All initial Agent Faithfulness scores were 1.0, including INC-002, illustrating that context consistency can coexist with incorrect attribution.

## 7. Evidence-Driven Improvement and Re-evaluation

TR-038 made one focused investigation improvement based on measured anchoring, repetition, and stopping failures: the prompt guidance and conditional broadening guardrail described above. The frozen dataset, ground truth, evaluators, thresholds, tools, and final RCA architecture remained unchanged. Model and tool budget also remained unchanged.

The [post-improvement summary](../experiments/comparison-post-tr038/summary.json) and [TR-039](TR039_POST_IMPROVEMENT_EVALUATION.md) give these Agent means. The first five rows are deterministic evidence/trace scores; the remaining rows are measured execution aggregates.

| Metric | Before | After |
|---|---:|---:|
| Evidence precision | 0.405 | 0.486 |
| Evidence recall | 0.744 | 0.867 |
| Evidence coverage | 0.800 | 0.867 |
| Empty-tool rate | 0.306 | 0.225 |
| Stop quality | 0.250 | 0.583 |
| Mean tool calls | 4.00 | 4.50 |
| Mean LLM calls | 7.50 | 8.33 |
| Mean runtime cost | ~$0.01164 | ~$0.01545 |

Mean latency was roughly similar in this particular run: 15.63 versus 15.18 seconds. Runtime cost increased by roughly one third. Broader investigation can cost more; the small latency difference does not establish a speed improvement.

The post-improvement mean LLM-judged Agent RCA score was **lower**, around 0.614 versus 0.771. This must not be attributed directly to TR-038: unchanged RAG also showed substantial run-to-run score variation, including INC-001 moving from approximately 0.762 to 0.100. Deterministic trace/evidence metrics and manual trace inspection therefore provide stronger evidence for TR-038's behavioral effect than this single judge-score comparison.

- **INC-001:** A broader initial metrics query gathered effectively the same useful evidence. The stop remained `consecutive_empty_results`; no RCA improvement was demonstrated.
- **INC-002:** The strongest scope-broadening improvement. The pre-run remained anchored on checkout-service; broader post-run deployment/metric queries found payment-service evidence. Precision/recall rose from 0/0 to 0.4/0.4, and stopping changed from `consecutive_empty_results` to `model_stop`. The final RCA still wrongly/incompletely attributed the problem to checkout-service: evidence gathering improved, but synthesis did not fully update.
- **INC-004:** A more focused search removed the broad log sweep, slightly improving precision (approximately 0.231 to 0.273). Stopping changed from `duplicate_selection` to `model_stop`, but RCA specificity still missed the exact `adFailure` trigger.
- **INC-006:** One fewer tool call removed the final broad log sweep. Stopping changed from `tool_budget_exhausted` to `duplicate_selection`; recall increased from approximately 0.667 to 1.0 and precision from 0.5 to approximately 0.545. RCA quality was preserved.

TR-038 improved several investigation behaviors, but better gathering did not consistently translate into better final RCA synthesis. Hypothesis updating and final causal reasoning remain important bottlenecks.

## 8. Limitations

- **Experimental scope:** Only six synthetic/adapted frozen incidents, no live production telemetry, and one pre-improvement and one post-improvement run. There is no statistical significance claim or basis for general production-performance conclusions.
- **Variability and comparability:** LLM generation and the LLM judge are stochastic; unchanged RAG scores varied between runs. RAG uses title/description while Agent context includes `suspected_services` when present. Evidence access differs intentionally.
- **Hypothesis state:** Current verification matches descriptions instead of stable hypothesis IDs. Assessment reasoning is not retained in hypothesis state, limiting inspection of hypothesis updates.
- **Grounding and synthesis:** Evidence-ID membership does not prove causal correctness. Final citation membership validation guarantees neither completeness nor a nonempty citation list when evidence was gathered. Better evidence does not guarantee better synthesis. Supporting-label completeness and hidden-trigger observability remain unresolved concerns.
- **Cost scope:** Recorded runtime cost may exclude evaluator/judge calls and must not be read as total evaluation cost.

## 9. Conclusion

The initial six-incident experiment showed higher mean RCA accuracy for the Agent than knowledge-only RAG, at substantially higher latency and runtime cost. Failure analysis identified evidence-gathering and stopping weaknesses. TR-038 improved deterministic evidence-recall, evidence-coverage, empty-tool, and stop-quality metrics; trace inspection supports meaningful scope-broadening and stopping improvements in several incidents.

Improved evidence gathering did not consistently improve final RCA synthesis. Hypothesis updating and causal synthesis remain important weaknesses. TraceRoot therefore shows promise for agentic evidence gathering within this controlled experiment, without claiming universal superiority.

Supporting documentation: [docs/ARCHITECTURE.md](ARCHITECTURE.md), [docs/DATASET_PROVENANCE.md](DATASET_PROVENANCE.md), [docs/TR037_FAILURE_ANALYSIS.md](TR037_FAILURE_ANALYSIS.md), and [docs/TR039_POST_IMPROVEMENT_EVALUATION.md](TR039_POST_IMPROVEMENT_EVALUATION.md).
