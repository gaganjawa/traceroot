"""Run from the repository root: uv run streamlit run app.py."""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
from openai import OpenAIError

from traceroot.data.loader import load_incident
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI
from traceroot.ui.helpers import (
    discover_incidents,
    evaluate_result,
    new_incident,
    run_investigation,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="TraceRoot", layout="wide")
st.title("TraceRoot")
st.caption("Evidence-grounded incident investigation")
with st.sidebar.expander("Help / Getting Started", expanded=True):
    st.markdown("""
**Your first investigation**

Set `OPENAI_API_KEY` in `.env` or your environment before running.
Investigations and evaluation make model API calls.

1. **Choose or enter an incident.** Start with an existing incident to use its
   local evidence. New incidents currently have no connected operational evidence.
2. **Set the tool budget.** `max_tool_calls` caps evidence queries (default 6),
   not all model requests. The agent may stop earlier.
3. **Start Investigation.** Wait for the completed result.
4. **Review hypotheses.** Check which possible causes remain open or were verified.
5. **Inspect the tool trace.** Expand each step to read its reasoning and observations.
6. **Inspect the stop reason.** Check why evidence gathering ended.
7. **Review the final RCA and evidence.** Match cited IDs to observations in the trace.
   An RCA without evidence is ungrounded.
8. **Optionally evaluate frozen incidents.** After completion, use **Evaluate Result**
   to see quality metrics. Ground truth is used only by the evaluator.

**Terms**

- **Hypothesis:** a possible cause. OPEN = unresolved, SUPPORTED = backed by
  evidence, REJECTED = not supported after verification.
- **Tool Call:** one query of local logs, metrics, deployments, or code changes.
- **Evidence ID:** an identifier for a returned record, linking a claim to evidence.
- **Stop Reason:** why queries ended: model choice (`model_stop`), budget reached
  (`tool_budget_exhausted`), repeated query blocked (`duplicate_selection`), or
  two empty queries in a row (`consecutive_empty_results`). It does not prove a cause.
- **Final RCA:** root-cause analysis with the proposed cause, affected service,
  explanation, confidence, and cited evidence IDs.

**Try it:** choose **Existing Evaluation Incident → INC-001**, set the budget
 to **4**, and start. Compare hypothesis statuses, expand each tool call, then
 check whether the final RCA cites the evidence you saw. Optionally evaluate it;
 the model's conclusions can vary between runs.

Completed results are saved to `experiments/results/ui/<unique-id>-agent.json`.
""")
mode = st.sidebar.selectbox("Mode", ["Existing Evaluation Incident", "New Incident"])
st.sidebar.write("Model:", LLM_MODEL_GPT_5_4_MINI)
budget = st.sidebar.number_input("max_tool_calls", min_value=1, value=6, step=1)
incident = None
incident_path = None
start = False

if mode == "Existing Evaluation Incident":
    paths = discover_incidents(Path("data/incidents"))
    if not paths:
        st.warning("No incidents found in data/incidents/.")
    else:
        incident_path = st.selectbox(
            "Incident", paths, format_func=lambda p: p.parent.name
        )
        try:
            incident = load_incident(incident_path)
            if incident.id != incident_path.parent.name:
                raise ValueError("Incident ID must match its dataset directory.")
            st.subheader("Incident")
            st.write("Title:", incident.title)
            st.write("Description:", incident.description)
            st.write("Start time:", incident.start_time.isoformat())
            st.write(
                "Suspected services:", ", ".join(incident.suspected_services) or "None"
            )
            start = st.button("Start Investigation", type="primary")
        except (OSError, ValueError):
            st.error(
                "The selected incident is missing or invalid. Check its incident.json file."
            )
            incident = None
else:
    st.info(
        "New incidents have no operational evidence source connected. The existing tools will return empty results; any RCA is ungrounded until evidence is supplied."
    )
    with st.form("new_incident"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        start_time = st.text_input(
            "Start time (ISO 8601, include timezone)",
            value=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        services = st.text_input("Suspected services (optional, comma-separated)")
        start = st.form_submit_button("Start Investigation", type="primary")
    if start:
        try:
            incident = new_incident(title, description, start_time, services)
        except ValueError:
            st.error("Enter a title, description, and valid ISO 8601 start time.")

context = (mode, str(incident_path))
if st.session_state.get("context") != context or start:
    st.session_state.pop("completed", None)
    st.session_state.pop("evaluation", None)
    st.session_state["context"] = context

if start and incident is not None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.error(
            "Set OPENAI_API_KEY in your environment or .env file before investigating."
        )
    else:
        try:
            with st.spinner("Investigating…"):
                record = run_investigation(
                    incident, int(budget), is_new=mode == "New Incident"
                )
            st.session_state["completed"] = (incident, record, incident_path)
        except FileNotFoundError:
            st.error("Incident evidence files are missing. Check the incident dataset.")
        except OpenAIError:
            st.error(
                "The LLM request failed. Check your API credentials, connectivity, and model configuration, then retry."
            )
        except Exception:
            logger.exception("Investigation failed")
            st.error(
                "Investigation failed. Check the dataset and model configuration, then retry."
            )

if completed := st.session_state.get("completed"):
    completed_incident, record, frozen_path = completed
    if mode == "New Incident":
        st.subheader("Incident")
        st.write("Title:", completed_incident.title)
        st.write("Description:", completed_incident.description)
        st.write("Start time:", completed_incident.start_time.isoformat())
        st.write(
            "Suspected services:",
            ", ".join(completed_incident.suspected_services) or "None",
        )
    st.caption(
        f"Model: {record.model} · Execution latency: {record.latency_ms:,.0f} ms"
    )
    if not record.evidence_ids:
        st.warning("No evidence was gathered. Treat the RCA as ungrounded.")
    st.subheader("Hypotheses")
    for hypothesis in record.hypotheses:
        st.write(f"{hypothesis.status.value.upper()}: {hypothesis.description}")
    if not record.hypotheses:
        st.info("No hypotheses returned.")
    st.subheader("Investigation Trace")
    for step, call in enumerate(record.tool_history, 1):
        with st.expander(
            f"Step {step}: {call.tool_name} · {call.service or 'All services'}"
        ):
            st.write("Tool name:", call.tool_name)
            st.write("Service:", call.service or "All services")
            st.write("Reasoning:", call.reasoning or "Not provided")
            st.write("Observations:")
            for observation in call.observations:
                st.text(observation)
            if not call.observations:
                st.write("None")
            st.write("Evidence IDs:", ", ".join(call.evidence_ids) or "None")
    st.write("Stop reason:", record.stop_reason or "Not provided")
    st.write("Stop reasoning:", record.stop_reasoning or "Not provided")
    st.subheader("Final RCA")
    st.write("Root cause:", record.result.root_cause)
    st.write("Affected service:", record.result.affected_service or "Unknown")
    st.write("Explanation:", record.result.explanation)
    st.write(
        "Confidence:",
        record.result.confidence
        if record.result.confidence is not None
        else "Not provided",
    )
    st.write("Evidence IDs:", ", ".join(record.result.evidence_ids) or "None")

    can_evaluate = (
        frozen_path is not None
        and (Path("data/ground_truth") / f"{record.incident_id}.json").is_file()
    )
    if can_evaluate and st.button("Evaluate Result"):
        try:
            with st.spinner("Evaluating completed result…"):
                st.session_state["evaluation"] = evaluate_result(record, frozen_path)
        except Exception:
            logger.exception("Evaluation failed")
            st.error(
                "Evaluation failed. Check evaluator dependencies, API settings, and ground-truth availability."
            )
    if evaluation := st.session_state.get("evaluation"):
        st.subheader("Evaluation")
        st.dataframe(
            [
                {
                    "Metric": metric.name.replace("_", " ").title(),
                    "Score": metric.score,
                    "Passed": metric.passed,
                    "Reason": metric.reason,
                }
                for metric in evaluation.metrics
            ],
            hide_index=True,
            use_container_width=True,
        )
        if evaluation.execution:
            st.write(evaluation.execution.model_dump(exclude_none=True))
