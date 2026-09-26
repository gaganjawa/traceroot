# TR-037 — Failure Analysis, Step 1

## Methodology

This report analyzes the six completed incidents in the current [TR-036 summary](../experiments/comparison/summary.json), using only that final run's raw records and evaluations as experimental evidence. No smoke runs, new experiments, or external sources are used. The six frozen ground-truth JSON files were read solely as the reference labels explicitly requested for this analysis; they are not embedded in the comparison artifacts. No source, prompts, thresholds, dataset, ground truth, or experiment outputs were changed.

For each incident, compare `hypotheses`, ordered `tool_history` observations/reasoning, gathered `evidence_ids`, final `result.evidence_ids`, final RCA, and evaluator reasons. “Labeled” means membership in ground truth's supporting-evidence set; being outside that set does **not** by itself establish that an observation is irrelevant. Precision measures cited-label overlap, recall measures cited-label coverage, and Evidence Coverage measures gathered-label coverage.

The records retain final hypothesis statuses, but not separate verification responses or rejected tool-selection payloads. Stage-specific diagnoses below are limited accordingly. Prompt-related explanations are hypotheses about observed model behavior, not proof of a defective prompt. Retrieved text is not stored in raw RAG records; baseline retrieval conclusions use source provenance and the generated explanation, not a reconstruction of the corpus. One run per incident cannot establish reproducibility or score variance.

## Incident findings

### INC-001 — Correct mechanism, missing initiating change

Sources: [RAG raw](../experiments/comparison/raw/INC-001-rag.json), [Agent raw](../experiments/comparison/raw/INC-001-agent.json), [evaluations](../experiments/comparison/evaluations/INC-001-agent-eval.json), [ground truth](../data/ground_truth/INC-001.json).

- **RAG:** Accuracy 0.7622. Checkout runbook retrieval supports a plausible database-pool contention diagnosis, appropriately qualified as uncertain. It misses the initiating reduction in pool maximum from 100 to 20.
- **Agent:** Accuracy 0.8622. Correctly links 20 active connections and 37 waiters (`METRIC-001-02/03`) to acquisition delays and timeouts (`LOG-001-02/03`). It likewise never identifies the configuration reduction. Confidence is 0.96 despite that unresolved initiating cause.
- **Trace:** `metrics(checkout-service)` → `logs(checkout-service)` → empty `metrics(payment-service)` → empty `metrics(database-service)` → `consecutive_empty_results`. No code-change query occurred. Four of five labeled items were gathered and cited; `CHANGE-001-01` was never gathered. Precision is 4/6, recall 4/5; the two additional citations are checkout latency and a database-timeout failure log, not obviously irrelevant observations.
- **Classification:** Insufficient evidence gathering, service/tool targeting, and guardrail stopping. The broad supported hypothesis describes checkout slowdown rather than the initiating change. This is an investigation-path/guardrail limitation with possible model-planning contribution; it is **not** a case of discarding already-gathered change evidence. RAG's missing incident-specific evidence is a baseline architectural limitation.

### INC-002 — Wrong service anchoring and no labeled evidence

Sources: [RAG raw](../experiments/comparison/raw/INC-002-rag.json), [Agent raw](../experiments/comparison/raw/INC-002-agent.json), [evaluation](../experiments/comparison/evaluations/INC-002-agent-eval.json), [ground truth](../data/ground_truth/INC-002.json).

- **RAG:** Accuracy 0.2037. Retrieves the payment runbook and correctly localizes authorization rejection to payment-service/provider interaction, but cannot identify the v3.7.0 currency serialization regression.
- **Agent:** Accuracy 0.7000 despite precision/recall 0. It recognizes provider validation rejection, but attributes malformed requests to **checkout-service**, while the label identifies **payment-service**. None of the five labeled supporting IDs was gathered; this is not a citation omission after successful gathering.
- **Trace:** All three hypotheses concern checkout-service. The first selection explicitly says “The hypotheses all point to checkout-service.” Only checkout logs, metrics, and deployments are queried; the last two return empty, triggering `consecutive_empty_results` after three executed calls. The only observations are successful request creation (`LOG-002-01`) and propagated provider-validation errors (`LOG-002-04/08`). All three are cited. There is no gathered currency-field, payment deployment, or mapping-change evidence.
- **Classification:** Hypothesis anchoring and service targeting lead to insufficient gathering; the empty-result guardrail terminates that path. Two checkout payload hypotheses end as `supported`, and the final RCA repeats their attribution with confidence 0.91. That suggests verification/synthesis overstatement relative to the observed logs, although separate verification reasoning is unavailable. These are model-planning/possible prompt-related and guardrail-related problems.
- **Evaluation caveat:** The accuracy reason rewards the general malformed-payload mechanism and notes omitted version/currency details, but does not explicitly penalize the wrong service attribution. Thus 0.7000 is not evidence of a fully correct diagnosis. Zero label overlap is arithmetically correct, yet the propagated error logs still provide symptom evidence; “no labeled evidence” is more precise than “no useful evidence.”

### INC-003 — Correct diagnosis with redundant, incompletely labeled citations

Sources: [RAG raw](../experiments/comparison/raw/INC-003-rag.json), [Agent raw](../experiments/comparison/raw/INC-003-agent.json), [evaluation](../experiments/comparison/evaluations/INC-003-agent-eval.json), [ground truth](../data/ground_truth/INC-003.json).

- **RAG:** Accuracy 1.0000. The order-processing runbook leads to the labeled inventory timeout → worker retry → backlog mechanism. The answer remains a plausible diagnosis from documentation, not operational confirmation.
- **Agent:** Accuracy 1.0000, recall 1.0000. It correctly connects queue depth 1,842, inventory p95 latency 5,200 ms, and repeated reservation timeouts/retries. It cites all four labeled items plus eight others: precision 4/12 = 0.3333.
- **Trace:** All-service metrics → order-worker logs → empty inventory-service deployments. It then stops on `duplicate_selection`; recorded stop reasoning again proposes inventory deployments while claiming the combination is unused. The supported dependency hypothesis and rejected saturation/liveness hypotheses broadly match the observed mechanism; absence of CPU saturation alone does not prove all forms of underprovisioning impossible.
- **Classification:** Excess/redundant citation and duplicate-selection stopping, not missing relevant evidence or wrong RCA synthesis. The repeated selection is a model state-tracking/possible prompt-related symptom interacting with the guardrail.
- **Data-label concern:** `LOG-003-04` through `LOG-003-10` repeat the same inventory timeout/retry messages as labeled `LOG-003-02/03`, yet are all counted as non-supporting. `METRIC-003-03` (31% worker CPU) is used as counterevidence to saturation. The low precision therefore conflates redundant or diagnostic evidence with irrelevant evidence. This is a concrete limitation of the supporting-ID labels, not an arithmetic error.

### INC-004 — Complete labeled evidence, unresolved trigger, inconsistent scoring severity

Sources: [RAG raw](../experiments/comparison/raw/INC-004-rag.json), [Agent raw](../experiments/comparison/raw/INC-004-agent.json), [RAG evaluation](../experiments/comparison/evaluations/INC-004-rag-eval.json), [Agent evaluation](../experiments/comparison/evaluations/INC-004-agent-eval.json), [ground truth](../data/ground_truth/INC-004.json).

- **RAG:** Accuracy 0.6937. Correctly localizes intermittent GetAds failures, but does not name the enabled `adFailure` fault. Retrieved sources are checkout, architecture, and payment documents; its explanation explicitly reports no ads-specific retrieved guidance. Faithfulness is 0.6667, so localization should not be mistaken for strong retrieved support.
- **Agent:** Accuracy 0.2559 with recall 1.0000. It correctly names ad-service/GetAds, alternating successes/failures, and a narrow blast radius, but leaves the trigger unresolved. All three labeled items were gathered and cited: `LOG-004-02/04` describe failed response generation and `METRIC-004-02` shows 0.11 error rate. None identifies fault activation.
- **Trace:** Ad logs → ad metrics → all-service logs → ad deployment → ad code changes. The broad log call repeats five already-seen ad logs, adding frontend fallback and healthy checkout. The deployment says no known functional changes; `CHANGE-004-02` explicitly says refactoring only, failure behavior unchanged. All 13 gathered IDs are cited (precision 3/13). All hypotheses remain open. A repeated code-change proposal triggers `duplicate_selection`, despite stop reasoning saying it has not been repeated.
- **Classification:** This is **not** failure to gather the labeled evidence. Final synthesis lacks the hidden trigger, but the gathered observations support only the failure phenotype, not `adFailure` activation. The artifacts do not justify calling this “ignored decisive evidence” or a demonstrably wrong service diagnosis. Supported concerns are evidence sufficiency relative to the label, broad citation, overlapping retrieval, and duplicate-selection stopping: dataset/evaluation-related and planning/guardrail-related.
- **Evaluation concern:** Both answers omit `adFailure` and describe the correct GetAds path, yet RAG receives 0.6937 and Agent 0.2559. The stored reasons treat the same omission with markedly different severity. This is a within-run consistency concern; it does not prove nondeterminism without repeated judgments. The label is more specific than the supporting observations retained in the trace, which establishes an observability gap rather than proving the label factually wrong.

### INC-005 — Memory degradation identified; exact fault mechanism unobserved

Sources: [RAG raw](../experiments/comparison/raw/INC-005-rag.json), [Agent raw](../experiments/comparison/raw/INC-005-agent.json), [evaluation](../experiments/comparison/evaluations/INC-005-agent-eval.json), [ground truth](../data/ground_truth/INC-005.json).

- **RAG:** Accuracy 0.0000. Checkout/order-processing/architecture retrieval steers the answer toward inventory latency and queue backlog, missing email-service memory degradation. This is an observed mismatch between retrieved guidance and the incident's causal mechanism; the artifacts do not establish whether a better chunk was available.
- **Agent:** Accuracy 0.8095, precision 7/10, recall 7/7. Email metrics show RSS rising from 128 to 782 MiB and processing p95 reaching 1,840 ms. `LOG-005-04/05` report rendering memory pressure and allocation failure. The final RCA correctly identifies progressive memory-related email degradation but cannot name `emailMemoryLeak` or padded email bodies from these observations.
- **Trace:** Email metrics → email logs → empty checkout metrics → `duplicate_selection` with checkout metrics proposed again. All seven labeled items were gathered and cited. The other citations are baseline memory and successful processing observations, which help establish progression rather than being plainly irrelevant.
- **Classification:** Baseline retrieval limitation; Agent duplicate-selection/stopping behavior; and a dataset/evaluation specificity gap for the exact injected mechanism. The backlog hypothesis is marked supported despite no queue-depth observation in the trace, suggesting a verification-specificity concern, but final synthesis appropriately emphasizes memory pressure. No evidence supports blaming failure to cite gathered relevant items.

### INC-006 — Correct RCA, citation omissions, and budget termination

Sources: [RAG raw](../experiments/comparison/raw/INC-006-rag.json), [Agent raw](../experiments/comparison/raw/INC-006-agent.json), [evaluation](../experiments/comparison/evaluations/INC-006-agent-eval.json), [ground truth](../data/ground_truth/INC-006.json).

- **RAG:** Accuracy 0.2019. Recognizes post-checkout cart clearing as the failing step but favors checkout-service/state persistence. Checkout/architecture/order-processing retrieval does not produce the cart-service EmptyCart mechanism.
- **Agent:** Accuracy 1.0000. Correctly identifies cart-service EmptyCart write failures after successful checkout. It gathers all six labeled items, but cites only four: precision 4/8 = 0.5000; recall 4/6 = 0.6667.
- **Trace:** Checkout logs → cart logs → cart metrics → checkout deployment → checkout code changes → all-service logs. The last call repeats six previously seen logs and adds only successful payment completion (`LOG-006-06`). Deployment/code-change observations describe tracing-only changes. The run exhausts six tools and nine LLM calls.
- **Citation distinction:** `METRIC-006-03/04`, the 0.01 GetCart/AddItem error rates, were gathered and are explicitly used in the explanation to contrast EmptyCart's 0.42 error rate, but are absent from `result.evidence_ids`. This is a concrete failure to cite used, labeled evidence. The four non-labeled citations are overall RPC errors, successful payment, and the deployment/code change; they supply context or negative evidence, not necessarily false support.
- **Classification:** Final citation selection, overlapping/excess gathering, tool prioritization, and budget-based stopping. These are synthesis/model-planning and architectural/guardrail concerns. There is no missing-labeled-evidence gathering failure or incorrect core RCA. The exact fault-routing detail is omitted but the evaluator accepts semantic equivalence, unlike its stricter treatment of the hidden fault name in INC-004.

## Cross-incident failure patterns

| Pattern | Incidents | Trace-backed distinction | Apparent locus |
|---|---|---|---|
| Documentation-only diagnosis lacks incident-specific causes | 001, 002, 004, 005, 006 | RAG supplies uncertainty or wrong causal localization; 003 is a successful runbook match | Baseline architecture/retrieval; corpus availability not established |
| Hypothesis/service anchoring limits evidence discovery | 002; narrower example in 001 | Checkout-only search in 002; empty dependency queries in 001; missing labeled evidence never gathered | Model planning, possible prompt contribution |
| Empty-result termination before complete coverage | 001, 002 | Coverage 4/5 and 0/5; both stop after two empty calls | Planning plus guardrail |
| Repeat selection ends otherwise informative investigations | 003, 004, 005 | Stop reasoning repeats an already executed tool/service query | Model state tracking plus guardrail; rejected payload not retained |
| Broad or redundant citations depress label precision | 003, 004; contextual examples in 001, 005, 006 | Correctly gathered observations outside a narrow label set count against precision | Citation selection plus dataset/evaluation labels |
| Gathered relevant evidence omitted from citations | 006 | GetCart/AddItem metrics used in explanation but missing from citation IDs | Final RCA citation synthesis |
| Full labeled coverage does not establish the hidden trigger | 004, 005 | Symptom evidence does not state injected fault activation/body padding | Dataset observability and evaluation specificity |
| Overlapping tool output despite unique selections | 004, 006 | All-service logs repeat prior service-filtered observations | Investigation architecture/planning; uniqueness metric limitation |
| Verification overstatement or weakly tested alternatives | 002; narrower concern in 005 | Checkout payload hypotheses supported from propagated errors; backlog supported without queue measurement | Verification/model behavior; prompt cause unproven |
| Semantic accuracy and operational correctness diverge | 002, 004, 006 | Wrong-service answer scores 0.7; similar GetAds descriptions score differently; fault-detail omissions treated differently | Evaluation consistency/scope |

No incident stopped with `model_stop`: two stopped on consecutive empty results, three on duplicate selection, and one on budget exhaustion. Tool Efficiency is 1.0 throughout even where results overlap or a duplicate selection terminates the run; its recorded reasons count unique **executed** tool/service pairs, not information gain or rejected selections. Stop Quality similarly reflects stop categories (duplicate selection scores 0.5), not proof of evidentiary completeness. All Agent Faithfulness scores are 1.0, including INC-002's misattribution: consistency with observed context does not establish agreement with the reference cause.

The unlabeled corroborating evidence in INC-003, scoring-severity difference in INC-004, and substantial accuracy credit despite wrong-service attribution in INC-002 are evaluation/data-label concerns, not established implementation bugs. These are metric-interpretation limitations, not evidence that telemetry or the corrected precision/recall threshold arithmetic is broken. All stored precision/recall pass flags agree with the 0.5 boundary.

## Cost and latency trade-offs

| Measure | RAG | Agent |
|---|---:|---:|
| Mean root-cause accuracy | 0.476934 | 0.771282 |
| Mean recorded latency | 3,178.51 ms | 15,634.02 ms |
| Mean estimated cost | $0.001581375 | $0.011635625 |
| Total estimated cost, six incidents | $0.00948825 | $0.06981375 |
| Total recorded LLM calls | 6 | 45 |
| Total recorded input + output tokens | 6,391 | 59,775 |

The Agent's mean recorded latency is 4.92× RAG's and its estimated cost is 7.36×. The trace shows multiple hypothesis, selection, verification, and synthesis stages, with additional selection calls on duplicate-stop paths. These figures are persisted experiment telemetry, not an all-in invoice for embeddings, evaluator calls, or total comparison wall time; there is no stage-level latency/cost breakdown in these artifacts. Costs use aggregate input/output estimates and do not distinguish cached input.

The observed accuracy means coexist with the evidence and evaluator caveats above. Six single runs provide descriptive results only; no overall superiority claim or failure ranking is made.

## Candidate Improvement Areas

- Hypothesis breadth and service attribution.
- Evidence-seeking priorities and causal-change coverage.
- Empty-result and duplicate-selection termination behavior.
- Overlapping tool results and information gain.
- Verification support criteria and uncertainty calibration.
- Final RCA citation completeness and selectivity.
- Baseline retrieval relevance and incident-specific evidence limits.
- Supporting-evidence label completeness and diagnostic counterevidence.
- Hidden-cause observability and semantic-evaluator consistency.
- Trace visibility into verification and rejected selections.
- Multi-stage latency, token consumption, and cost accounting scope.
