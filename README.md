# TraceRoot

**Evidence-Grounded Production Incident Investigator**

TraceRoot is an AI engineering capstone comparing two approaches to root-cause analysis (RCA) on controlled software incident datasets.

> Can agentic evidence gathering improve root-cause identification and evidence grounding compared with knowledge-only RAG for software production incidents?

## Demo

🎥 [Watch the TraceRoot Capstone Demo](https://drive.google.com/file/d/1UioGv0xEvZlbOhue6gxQy69zuQvwQzDG/view?usp=sharing)

## Key Results

Initial six-incident comparison:

| Measure | RAG | Agent |
|---|---:|---:|
| Mean RCA accuracy | ~0.477 | ~0.771 |
| Mean latency | ~3.18 s | ~15.63 s |
| Mean runtime cost | ~$0.00158 | ~$0.01164 |

Post-TR-038 deterministic Agent metrics:

| Metric | Before | After |
|---|---:|---:|
| Evidence precision | 0.405 | 0.486 |
| Evidence recall | 0.744 | 0.867 |
| Evidence coverage | 0.800 | 0.867 |
| Empty-tool rate | 0.306 | 0.225 |
| Stop quality | 0.250 | 0.583 |

The improvement increased evidence gathering quality and stopping behavior, but also increased average tool/LLM usage and runtime cost.

TR-038 is **not shown to improve RCA accuracy**: the post-improvement LLM-judged Agent RCA mean was lower in that single run (0.614 vs 0.771). Unchanged RAG scores also varied substantially between runs. The strongest evidence for TR-038 is therefore the deterministic trace/evidence metrics and manual trace inspection, not a single LLM-judge comparison.

See [Architecture and demo walkthrough](docs/ARCHITECTURE.md) for Mermaid diagrams, runtime flow, and experimental boundaries.

## Documentation

- [System design](docs/SYSTEM_DESIGN.md)
- [Architecture and demo walkthrough](docs/ARCHITECTURE.md)
- [Capstone report](docs/CAPSTONE_REPORT.md)
- [TR-037 failure analysis](docs/TR037_FAILURE_ANALYSIS.md)
- [TR-039 post-improvement evaluation](docs/TR039_POST_IMPROVEMENT_EVALUATION.md)
- [Dataset provenance](docs/DATASET_PROVENANCE.md)

## Current state — v1.1.0: Live Evidence & Grounded RCA

TraceRoot v1.1.0 is released. It includes a knowledge-only RAG baseline and a live-capable agentic investigator with runtime incident intake, fixture/live evidence routing, CLI and basic Streamlit live modes, independently verified RCA claims, and validated telemetry with preserved labels. Completed investigations persist their results and traces. Evaluation combines DeepEval with deterministic evidence and trace metrics; runtime instrumentation records latency, token usage, and estimated cost.

Current validation baseline: **964 tests passed**, with Ruff lint and formatting checks passing. Real smoke validation exercised the Prometheus live CLI path with label-rich metrics in persisted traces, distinct Loki evidence IDs for same-message records from `instance-a` and `instance-b`, and an LLM-backed RCA flow that avoided unsupported causal conclusions. These checks demonstrate execution and grounding behavior, not production readiness or measured accuracy gains.

The historical `v1.0-capstone` release evaluates RAG and Agent approaches on the same frozen six-incident dataset, includes pre- and post-TR-038 comparisons, and provides both CLI and Streamlit demos. See the [failure analysis](docs/TR037_FAILURE_ANALYSIS.md) and [post-improvement evaluation](docs/TR039_POST_IMPROVEMENT_EVALUATION.md) for detailed methods, results, and limitations.

## Two approaches

| Approach | Input and evidence | Output |
|---|---|---|
| Knowledge-only RAG baseline | Incident title/description plus engineering knowledge retrieved from Qdrant | Structured RCA and separate retrieval provenance; operational `evidence_ids` remain empty |
| Agentic investigation | Incident context, hypotheses, and selected logs, metrics, deployments, and code changes from frozen local files or configured live providers | Structured RCA checked against gathered observations, plus investigation trace |

The agent does not retrieve the RAG knowledge corpus. Both approaches return `RCAResult`, and ground truth is evaluator-only: it is used for evaluation, never supplied to either approach at runtime. Inputs are not fully at parity: RAG retrieval uses the incident title and description, while the Agent receives richer incident context, including `suspected_services` when present.

## Evaluation dataset

The frozen evaluation set contains six incidents. `INC-001` to `INC-003` are controlled synthetic incidents; `INC-004` to `INC-006` are synthetic/adapted scenarios based on OpenTelemetry Demo / Astronomy Shop failure modes. They are not captured production traces.

## Setup and run

From the repository root, with Python 3.12+ and `uv` installed:

```bash
uv sync
cp .env.example .env
```

If `.env` already exists, keep it and fill in any missing settings instead of copying over it. Set `OPENAI_API_KEY` for live runs. The template defaults to `gpt-5.4-mini` for generation and `text-embedding-3-small` for embeddings, with an optional `OPENAI_BASE_URL` override. The knowledge index expects 1536-dimensional embeddings.

Run the tests (external model calls are mocked; a placeholder key satisfies embedding-module initialization):

```bash
OPENAI_API_KEY=test-key uv run pytest
```

Run the INC-001 baseline with real model calls and the local knowledge corpus:

```bash
uv run python scripts/run_baseline.py
```

This embeds the knowledge corpus, creates an in-memory Qdrant index, generates an RCA, and writes `experiments/results/INC-001-rag_baseline.json`. No Qdrant server is required for this script; it does not use the template's `QDRANT_URL`.

Run the fixture-backed agent with real model calls through its Python entry point:

```bash
uv run python - <<'PY'
from pathlib import Path
from traceroot.data.loader import load_incident
from traceroot.experiments.agent import run_agent_experiment

record = run_agent_experiment(
    incident=load_incident(Path("data/incidents/INC-001/incident.json")),
    output_path=Path("experiments/results/INC-001-agent.json"),
    max_tool_calls=4,
)
print(record.model_dump_json(indent=2))
PY
```

These examples make model API calls and overwrite the named output artifact if it already exists. The Agent example uses local fixtures; no running production or demo service is required. To query live providers, use [Live CLI investigations](#live-cli-investigations).

## Project structure

```text
data/incidents/       Six frozen incident descriptions and operational evidence
data/knowledge/       General engineering documentation for RAG
data/ground_truth/    Evaluator-only answers and supporting evidence labels
data/evaluation/      Retrieval benchmark
src/traceroot/        Domain models, data loading, RAG, baseline, tools,
                      agent, intake, live integrations, backend routing,
                      MCP, experiment persistence, and evaluation contracts
scripts/run_baseline.py            RAG baseline runner
scripts/investigate.py             Agent CLI / demo harness
scripts/run_comparison.py          Comparative experiment runner
tests/                             Automated tests
experiments/results/               Generated experiment artifacts
experiments/comparison/            Pre-TR-038 evaluation artifacts
experiments/comparison-post-tr038/ Post-TR-038 evaluation artifacts
docs/                              Project architecture and demo explanation
docs/TR037_FAILURE_ANALYSIS.md
docs/TR039_POST_IMPROVEMENT_EVALUATION.md
```

## Release scope and future work

v1.1.0 — **Live Evidence & Grounded RCA** adds runtime intake, production-style evidence integrations, RCA claim grounding, and telemetry validation/provenance through TR-048. The frozen capstone comparisons remain historical results; they have not been rerun to measure these additions. The Streamlit UI remains a basic demo/presentation layer, and TraceRoot is not production-ready.

Pending work includes **TR-049 — Bounded Evidence Context**, failed investigation persistence, fuller query/source provenance, and remote MCP transport. MCP evidence tools and Agent integration already exist, but calls remain in-process. See the [project board](PROJECT_BOARD.md) for the ordered backlog.

### Live evidence and grounding

| Source | Evidence and boundary |
|---|---|
| Loki | Log observations with complete stream labels. Canonical labels, the raw source timestamp, and message determine live log identity; log wording is not automatically true. |
| Prometheus-compatible API | Strict matrix responses with finite samples. Complete labels, including route/status/method/instance/quantile/le when returned, remain visible in evidence and trace observations. |
| GitHub releases | Release metadata used as a deployment proxy; not proof of a production rollout. |
| GitHub commits | Repository code-change evidence; not proof that the code was deployed. |

Malformed Loki/Prometheus HTTP 200 responses, unsupported result types, and malformed records fail explicitly instead of becoming empty evidence. Prometheus NaN/Inf samples are rejected; Loki service selectors use JSON string escaping. Prometheus IDs and fixture IDs are unchanged, and historical evidence JSON without labels still loads.

Citation membership alone is insufficient. After hypothesis verification and RCA candidate generation, a separate LLM claim assessment and deterministic validation check causal support, evidence/observation mappings, rejected hypotheses, and confidence/wording. Assessments are `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED`. Unqueried sources, queried-empty sources, and sources with evidence are distinguished: an empty deployment query is a limitation, not proof no deployment occurred. Partial support requires cautious language. A rejected candidate can be repaired once and independently reverified; unresolved support leads to cautious fallback. Initial generation failures and investigations with no evidence can still raise errors.

## Streamlit UI

The Streamlit app is a basic demo/presentation layer over the investigation and evaluation flows. Frozen incidents use local evidence; **Live Incident** creates a runtime incident and queries configured providers. It is not a production dashboard.

From the repository root, install dependencies with `uv sync`, configure
`OPENAI_API_KEY` in `.env` or the environment, then run:

```bash
uv run streamlit run app.py
```

Choose **Existing Evaluation Incident** to investigate a fixture, or **Live Incident**
to investigate your configured live sources. Set the tool-call budget and click
**Start Investigation**. The UI uses the existing agent experiment runner and
displays the incident ID, hypotheses, tool observations, evidence IDs, stop
reasoning, and final RCA with confidence. Fixture/demo results are saved with
unique filenames under `experiments/results/ui/`.

For **Live Incident**, configure the environment settings listed under
[Live CLI investigations](#live-cli-investigations), then enter a title,
description, timezone-aware ISO start time, and optional comma-separated suspected
services. Live results are saved to
`experiments/results/live/<runtime-id>-agent.json`; the UI displays the saved path.

**New Incident** remains a demo that requires no manual JSON files and supplies
empty local evidence. Its no-evidence guardrail prevents final RCA generation.

For completed frozen incidents, **Evaluate Result** invokes the existing evaluation
runner and displays its available metrics and execution measurements. Ground truth
is loaded only within this evaluator path. Evaluation uses the development
`deepeval` dependency (included by `uv sync`) and may make additional model API calls.

### First-time help

The Streamlit sidebar has an expanded **Help / Getting Started** walkthrough,
key terms, and an example investigation. For CLI help without making API calls:

```bash
uv run python scripts/investigate.py --help
uv run python scripts/investigate.py --getting-started
```

Try either investigation from the repository root after configuring your API key:

```bash
uv run python scripts/investigate.py --incident-id INC-001
uv run python scripts/investigate.py --incident-id INC-002 --max-tool-calls 4
```

`--incident-id` selects a folder in `data/incidents/`. `--max-tool-calls` limits
queries for evidence (default 6); it does not limit total model requests. The CLI
saves the full trace to `experiments/results/<incident-id>-agent.json`, overwriting
that incident's previous CLI result. The walkthrough explains how to interpret
hypotheses, evidence IDs, stop reasons, and the final root-cause analysis.


### Live CLI investigations

Configure `OPENAI_API_KEY` and these required live settings in your environment or
`.env`: `TRACEROOT_LOKI_BASE_URL`, `TRACEROOT_PROMETHEUS_BASE_URL`,
`TRACEROOT_GITHUB_REPO` (`owner/repo`), and `TRACEROOT_GITHUB_SERVICE`.
`TRACEROOT_GITHUB_TOKEN` is optional; `.env.example` documents the remaining settings.

```bash
uv run python scripts/investigate.py --live \
  --title "Checkout failures" \
  --description "Checkout requests are timing out." \
  --start-time "2026-10-03T12:00:00+05:30" \
  --suspected-service checkout-service \
  --max-tool-calls 4
```

`--live` and `--incident-id` are mutually exclusive. Live mode requires a nonblank
title and description and an explicit timezone-aware ISO start time (`Z` or an
offset). Providers query windows around that time. `--suspected-service` is optional
and repeatable; these services are leads, not forced tool filters. Both GitHub
providers use the single repository/service mapping in configuration.

Live bootstrap uses environment-driven `LiveEvidenceConfig` to construct the providers and an evidence backend router. `RuntimeIncidentRegistry` registration selects live versus fixture evidence behind the unchanged tool contract.

The CLI creates and registers a runtime incident, explicitly activates live routing,
and runs the existing agent pipeline. It prints the generated incident ID and saves
the trace to `experiments/results/live/<runtime-id>-agent.json`. It creates no fixture
incident files. Live runs make model and provider API calls. Missing/invalid live
inputs or configuration exit with code 2; execution failures exit with code 1.
No evidence means the existing guardrail prevents final RCA generation.

Existing fixture commands, result paths, and overwrite behavior remain unchanged.
Streamlit live mode uses the same runtime components with an investigation-scoped executor. Failed investigation persistence and bounded evidence context remain pending.
