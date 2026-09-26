# TR-039 — Post-Improvement Comparative Evaluation

## 1. Experiment Setup

TR-039 evaluates the effect of the single TR-038 investigation improvement on TraceRoot's Agent behavior.

Configuration:

- Incidents: `INC-001` through `INC-006`
- Model: `gpt-5.4-mini`
- RAG `top_k`: `3`
- Agent `max_tool_calls`: `6`
- Pre-improvement results: `experiments/comparison/`
- Post-improvement results: `experiments/comparison-post-tr038/`

The evaluation dataset and ground truth remained frozen. The evaluators, thresholds, model, incident set, and tool-call budget were unchanged. The only intended behavioral change was the TR-038 Agent investigation update: prompt guidance for broader, less repetitive evidence gathering plus a deterministic guardrail that broadens repeated same-service selections after an empty targeted result.

The post-improvement run completed all six incidents successfully with zero experiment failures and produced the expected 25 artifacts.

## 2. Aggregate Results

| Metric | Pre TR-038 | Post TR-038 | Direction |
|---|---:|---:|---|
| Agent mean RCA accuracy | 0.771 | 0.614 | Lower in this run |
| Mean evidence precision | 0.405 | 0.486 | Improved |
| Mean evidence recall | 0.744 | 0.867 | Improved |
| Mean evidence coverage | 0.800 | 0.867 | Improved |
| Mean empty-tool rate | 0.306 | 0.225 | Improved |
| Mean stop quality | 0.250 | 0.583 | Improved |
| Mean tool calls | 4.00 | 4.50 | Higher |
| Mean LLM calls | 7.50 | 8.33 | Higher |
| Mean latency | 15.63 s | 15.18 s | Roughly unchanged |
| Mean estimated cost | $0.01164 | $0.01545 | Higher |

The post-TR-038 run produced a lower mean LLM-judged RCA score, but this cannot be attributed solely to TR-038. The unchanged RAG baseline also showed substantial run-to-run score variation. For example, INC-001 RAG root-cause accuracy moved from approximately `0.762` before TR-038 to `0.100` after TR-038 even though the RAG implementation was unchanged.

For that reason, the strongest evidence for TR-038 should come from deterministic evidence/trace metrics and direct trace inspection rather than from a single LLM-judge score comparison.

## 3. Per-Incident Analysis

### INC-001

The post-TR-038 investigation broadened its first metrics query from `checkout-service` to all services (`service=None`).

However, the useful evidence gathered was effectively unchanged. Both runs collected the same checkout metrics and logs, then performed empty metric queries against `payment-service` and `database-service`.

The stop reason remained:

`consecutive_empty_results`

The final diagnosis remained centered on database connection contention causing checkout latency and timeouts. The post-TR-038 run did not identify the more specific ground-truth configuration change that reduced the checkout database connection-pool size.

**Assessment**

- Scope broadening: minor change
- Evidence improvement: not demonstrated
- Stopping improvement: none
- RCA improvement: not demonstrated

### INC-002

INC-002 showed the clearest investigation improvement.

Before TR-038, the Agent remained anchored on `checkout-service`:

1. `logs / checkout-service`
2. `metrics / checkout-service`
3. `deployments / checkout-service`

The final two calls returned no evidence, and the investigation stopped with:

`consecutive_empty_results`

It gathered none of the labeled ground-truth-supporting evidence.

After TR-038, the investigation path became:

1. `logs / checkout-service`
2. `metrics / checkout-service`
3. `deployments / all services`
4. `code_changes / checkout-service`
5. `metrics / all services`

The broader queries discovered:

- the `payment-service v3.7.0` deployment
- payment-service authorization-failure metrics

Evidence coverage improved from `0.0` to `0.4`, and evidence precision/recall improved from `0.0 / 0.0` to `0.4 / 0.4`.

The stop reason improved from:

`consecutive_empty_results`

to:

`model_stop`

Despite the improved evidence gathering, the final RCA still attributed the invalid authorization requests to `checkout-service` rather than identifying the payment-service currency-serialization change.

**Assessment**

- Scope broadening: substantially improved
- Evidence gathering: improved
- Stopping: improved
- Final RCA: still incomplete/incorrect
- Remaining limitation: hypothesis anchoring and final causal synthesis

This case demonstrates that better evidence gathering does not automatically guarantee a better final diagnosis.

### INC-003

INC-003 retained a correct final RCA in both runs.

Post-TR-038:

- root-cause accuracy remained `1.0`
- evidence recall remained `1.0`
- evidence coverage remained `1.0`
- evidence precision remained `0.333`

The post-improvement Agent used more investigation calls without producing a clear final-answer improvement.

**Assessment**

- RCA quality: preserved
- Evidence recall/coverage: preserved
- Investigation cost: increased
- Clear TR-038 benefit: not demonstrated from final-answer quality alone

### INC-004

Before TR-038, the investigation used:

1. `logs / ad-service`
2. `metrics / ad-service`
3. `logs / all services`
4. `deployments / ad-service`
5. `code_changes / ad-service`

After TR-038, the path was more focused:

1. `metrics / ad-service`
2. `logs / ad-service`
3. `deployments / ad-service`
4. `code_changes / ad-service`

The post-TR-038 run avoided the additional all-service log sweep while retaining the useful ad-service evidence.

Evidence precision improved slightly from approximately `0.231` to `0.273`, while evidence recall and coverage remained `1.0`.

The stop reason improved from:

`duplicate_selection`

to:

`model_stop`

However, the final RCA remained unable to identify the specific `adFailure` trigger. Both runs localized the problem to intermittent GetAds/ad-service failures but left the deeper trigger unresolved.

**Assessment**

- Search efficiency: improved
- Evidence precision: slightly improved
- Stopping: improved
- Evidence recall/coverage: preserved
- RCA specificity: essentially unchanged
- Remaining limitation: causal synthesis and evidence specificity

### INC-005

INC-005 remained a strong Agent case.

Post-TR-038:

- RCA accuracy remained high (`0.728` in the post run)
- evidence precision remained `0.7`
- evidence recall remained `1.0`
- evidence coverage remained `1.0`

The post run used slightly more investigation work, but there was no major behavioral regression and no clear final-answer gain attributable to TR-038.

**Assessment**

- Strong RCA behavior: preserved
- Evidence quality: preserved
- Investigation cost: slightly increased
- Major regression: none demonstrated

### INC-006

Before TR-038, the Agent used all six allowed tool calls:

1. `logs / checkout-service`
2. `logs / cart-service`
3. `metrics / cart-service`
4. `deployments / checkout-service`
5. `code_changes / checkout-service`
6. `logs / all services`

It stopped with:

`tool_budget_exhausted`

After TR-038, the investigation stopped after five calls:

1. `logs / checkout-service`
2. `logs / cart-service`
3. `metrics / cart-service`
4. `deployments / checkout-service`
5. `code_changes / checkout-service`

The final all-service log sweep was no longer performed.

The stop reason changed to:

`duplicate_selection`

Evidence recall improved from approximately `0.667` to `1.0`, and precision improved from `0.500` to approximately `0.545`. The RCA remained strong and continued to identify intermittent `cart-service` EmptyCart write failures.

**Assessment**

- Search efficiency: improved
- Evidence quality: slightly improved
- Stopping: improved
- RCA quality: preserved
- Obvious regression: none

## 4. Trace-Level Findings

The post-TR-038 traces show several consistent behavioral patterns.

### Improved scope broadening

INC-002 provides the clearest example. The Agent moved from repeatedly investigating only `checkout-service` to using all-service deployment and metric queries, which surfaced payment-service evidence that the pre-improvement investigation never found.

INC-001 also began with a broader metrics query, although this did not materially improve the final evidence set.

### Better stopping behavior

The post-improvement run produced fewer poor stopping outcomes.

Examples:

- INC-002: `consecutive_empty_results` → `model_stop`
- INC-004: `duplicate_selection` → `model_stop`
- INC-006: `tool_budget_exhausted` → `duplicate_selection`

This is consistent with the aggregate stop-quality improvement from `0.250` to `0.583`.

### Better evidence coverage and recall

Mean evidence recall increased from `0.744` to `0.867`, and mean evidence coverage increased from `0.800` to `0.867`.

The strongest example was INC-002, where the Agent moved from finding no labeled supporting evidence to finding payment-service deployment and metric evidence.

### Evidence quality does not guarantee RCA quality

INC-002 is the clearest example of the remaining limitation. The Agent successfully broadened its investigation and gathered payment-service evidence, but its final RCA remained anchored on `checkout-service`.

This suggests that evidence access is no longer the only bottleneck. Hypothesis updating, causal interpretation, and final RCA synthesis remain important limitations.

### Broader exploration has a cost

The Agent performed more tool and LLM calls on average after TR-038. This improved evidence gathering in some cases but increased token usage and cost.

The goal of future work should therefore not be simply to broaden every investigation. It should be to broaden selectively when evidence is insufficient or contradictory.

## 5. Cost and Latency Trade-offs

Mean estimated runtime cost increased from approximately:

`$0.01164`

to:

`$0.01545`

per Agent investigation, an increase of roughly 33%.

Mean tool calls increased from `4.00` to `4.50`, and mean LLM calls increased from `7.50` to `8.33`.

Mean observed latency changed from approximately `15.63 s` to `15.18 s`.

The small latency reduction should not be interpreted as evidence that TR-038 made the Agent faster. With only six incidents and stochastic LLM execution, the two values are effectively similar for this experiment.

The cost increase is more directly explained by the increase in investigation and LLM calls.

The recorded costs represent experiment/runtime generation costs. They should not be interpreted as total evaluation cost if LLM-as-a-judge evaluation calls are not included in the execution metrics.

## 6. Evaluation Variability and Limitations

Several limitations constrain the conclusions that can be drawn from TR-039.

### Small evaluation set

The comparison contains only six incidents. Results are useful for capstone-level comparative analysis but do not establish general production performance.

### Single pre/post run

Only one frozen pre-improvement run and one post-improvement run were compared. No repeated-run confidence interval or statistical significance analysis was performed.

### Stochastic generation

Both RAG and Agent generation use an LLM, so outputs can differ between runs even when code and inputs remain unchanged.

### LLM-judge variability

Root-cause accuracy, faithfulness, and relevancy use LLM-based evaluation. These scores can also vary between runs.

This is visible in the unchanged RAG baseline. RAG RCA scores changed substantially for some incidents despite no RAG code change. Therefore, a change in Agent RCA score alone cannot be treated as causal evidence for or against TR-038.

### Greater confidence in deterministic behavioral metrics

Evidence precision, evidence recall, evidence coverage, tool efficiency, empty-tool rate, and stop behavior are deterministic for a given saved trace.

These metrics, together with direct trace inspection, provide stronger evidence for the specific TR-038 investigation changes than the single-run LLM-judge RCA score difference.

### Synthetic/adapted evaluation surface

The incident dataset is frozen and includes synthetic/adapted scenarios, including scenarios based on OpenTelemetry Demo failure modes. This improves reproducibility but does not represent the full complexity of live production telemetry.

### Runtime cost scope

The persisted runtime cost reflects the instrumented experiment-generation calls. If evaluation/judge calls are not included in those execution metrics, the values should not be presented as total end-to-end evaluation cost.

## 7. Conclusion

TR-038 improved several deterministic investigation-quality metrics, particularly evidence recall, evidence coverage, empty-tool behavior, and stopping quality.

Trace inspection supports meaningful improvement in scope broadening for cases such as INC-002 and more focused or earlier stopping in INC-004 and INC-006.

However, improved evidence gathering did not consistently translate into more accurate final RCA synthesis. INC-002 in particular gathered substantially better cross-service evidence but still produced a checkout-service-anchored final diagnosis.

The post-improvement experiment therefore suggests that TraceRoot's remaining bottleneck is not only evidence access. Hypothesis updating and final causal reasoning remain important areas for future improvement.

Given the small dataset, single-run comparison, and LLM/evaluator stochasticity, TR-039 does not claim statistical significance or universal improvement. Its strongest finding is narrower: the TR-038 investigation change improved several deterministic evidence-gathering and stopping behaviors while leaving final RCA synthesis as an unresolved limitation.
