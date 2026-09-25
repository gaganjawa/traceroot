# TraceRoot

**Evidence-Grounded Production Incident Investigator**

TraceRoot is an AI engineering capstone comparing two approaches to root-cause analysis (RCA) on controlled software incident datasets.

> Can agentic evidence gathering improve root-cause identification and evidence grounding compared with knowledge-only RAG for software production incidents?

## Current state — through TR-026

The core implementation includes a knowledge-only RAG baseline, deterministic operational evidence tools, an agentic investigation loop with guardrails, final RCA generation, and JSON experiment/trace persistence. The repository contains three synthetic incidents, five engineering knowledge documents, and a separate 10-query retrieval benchmark with Recall@K evaluation.

TR-025 and TR-026 are implemented and committed. [The project board](PROJECT_BOARD.md) tracks completed work and the remaining evaluation and delivery tasks. Functional tests and smoke runs establish execution behavior, **not measured RCA accuracy or agent superiority**. Final comparative evaluation and failure analysis are pending.

## Two approaches

| Approach | Input and evidence | Output |
|---|---|---|
| Knowledge-only RAG baseline | Incident title/description plus engineering knowledge retrieved from Qdrant | Structured RCA and separate retrieval provenance; operational `evidence_ids` remain empty |
| Agentic investigation | Incident context, hypotheses, and selected logs, metrics, deployments, and code changes from local incident files | Structured RCA referencing gathered evidence, plus investigation trace |

The current agent does not retrieve the RAG knowledge corpus. Both approaches return `RCAResult`. Ground truth is evaluator-only and excluded from runtime inputs. The intended comparison uses the same frozen incidents; incident-field parity, including `suspected_services`, still needs resolution before final experiments.

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
data/incidents/       Incident descriptions and operational evidence
data/knowledge/       General engineering documentation for RAG
data/ground_truth/    Evaluator-only answers and supporting evidence labels
data/evaluation/      Retrieval benchmark
src/traceroot/        Domain models, data loading, RAG, baseline, tools,
                      agent, experiment persistence, and evaluation contracts
scripts/              Baseline run entry point
tests/                Automated tests
experiments/results/  Generated experiment artifacts
docs/                 Project architecture and demo explanation
```

## Remaining work

- TR-027–TR-034: RCA and evidence evaluators, quality/trace evaluation, efficiency instrumentation, and unified evaluation runner.
- TR-035: expand and freeze the final dataset, retaining the three synthetic cases and adding planned OpenTelemetry Demo / Astronomy Shop-derived scenarios (ad service failure, email memory leak, cart service failure). These additions are not yet present.
- TR-036–TR-039: comparative experiments, failure analysis, evidence-driven improvement, and re-evaluation.
- Complete delivery documentation and demo. MCP integration remains optional stretch work.

Retrieval quality is evaluated separately from RCA quality. No final evaluation scores are claimed here.
