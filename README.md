# TraceRoot

**Evidence-Grounded Production Incident Investigator**

TraceRoot is an AI engineering capstone comparing two approaches to root-cause analysis (RCA) on controlled software incident datasets.

> Can agentic evidence gathering improve root-cause identification and evidence grounding compared with knowledge-only RAG for software production incidents?

## Current state — first release through TR-039

TraceRoot includes a knowledge-only RAG baseline and an agentic investigator with deterministic logs, metrics, deployments, and code-change tools. The agent generates and verifies hypotheses, gathers operational evidence, and produces an RCA; investigation traces and results are persisted. Evaluation combines DeepEval with deterministic evidence and trace metrics, and runtime instrumentation records latency, token usage, and estimated cost.

The first release evaluates RAG and Agent approaches on the same frozen six-incident dataset, includes pre- and post-TR-038 comparisons, and provides both CLI and Streamlit demos. See the [failure analysis](docs/TR037_FAILURE_ANALYSIS.md) and [post-improvement evaluation](docs/TR039_POST_IMPROVEMENT_EVALUATION.md) for detailed methods, results, and limitations.

## Two approaches

| Approach | Input and evidence | Output |
|---|---|---|
| Knowledge-only RAG baseline | Incident title/description plus engineering knowledge retrieved from Qdrant | Structured RCA and separate retrieval provenance; operational `evidence_ids` remain empty |
| Agentic investigation | Incident context, hypotheses, and selected logs, metrics, deployments, and code changes from local incident files | Structured RCA referencing gathered evidence, plus investigation trace |

The agent does not retrieve the RAG knowledge corpus. Both approaches return `RCAResult`, and ground truth is evaluator-only: it is used for evaluation, never supplied to either approach at runtime. Inputs are not fully at parity: RAG retrieval uses the incident title and description, while the Agent receives richer incident context, including `suspected_services` when present.

## Evaluation dataset

The frozen evaluation set contains six incidents. `INC-001` to `INC-003` are controlled synthetic incidents; `INC-004` to `INC-006` are synthetic/adapted scenarios based on OpenTelemetry Demo / Astronomy Shop failure modes. They are not captured production traces.

## Evaluation results

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

Run the live INC-001 baseline:

```bash
uv run python scripts/run_baseline.py
```

This embeds the knowledge corpus, creates an in-memory Qdrant index, generates an RCA, and writes `experiments/results/INC-001-rag_baseline.json`. No Qdrant server is required for this script; it does not use the template's `QDRANT_URL`.

Run the live agent through its Python entry point:

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

Live runs make model API calls and overwrite the named output artifact if it already exists. Agent evidence tools read local fixtures; no running production or demo service is required.

## Project structure

```text
data/incidents/       Six frozen incident descriptions and operational evidence
data/knowledge/       General engineering documentation for RAG
data/ground_truth/    Evaluator-only answers and supporting evidence labels
data/evaluation/      Retrieval benchmark
src/traceroot/        Domain models, data loading, RAG, baseline, tools,
                      agent, experiment persistence, and evaluation contracts
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

The first release uses reproducible, file-backed evidence. MCP integration is stretch work. Live incident intake, live observability/deployment/Git integrations, and production deployment are future work.

## Streamlit UI

The Streamlit app is a demo/presentation layer over the investigation and evaluation flows. Frozen incidents have local operational evidence; manually created incidents currently have no live telemetry integration.

From the repository root, install dependencies with `uv sync`, configure
`OPENAI_API_KEY` in `.env` or the environment, then run:

```bash
uv run streamlit run app.py
```

Choose an existing evaluation incident or enter a new incident, set the tool-call
budget, and click **Start Investigation**. The UI uses the existing agent experiment
runner and displays hypotheses, tool observations, stop reasoning, and the final
RCA. Completed experiment records are saved with unique filenames under
`experiments/results/ui/`.

New incidents require no manual JSON files. Since operational tools currently
read local datasets only, manually created incidents have no operational evidence
or live telemetry, and their RCA should be treated as ungrounded.

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
