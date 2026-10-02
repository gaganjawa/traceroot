"""Run from the repository root: uv run streamlit run app.py."""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from httpx import HTTPError
from openai import OpenAIError
from pydantic import ValidationError

from traceroot.config import load_live_evidence_config
from traceroot.data.loader import load_incident
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI
from traceroot.ui.helpers import (
    discover_incidents,
    evaluate_result,
    new_incident,
    new_live_incident,
    run_investigation,
    run_live_investigation,
)

logger = logging.getLogger(__name__)
load_dotenv()

st.set_page_config(page_title="TraceRoot", layout="wide")
st.title("TraceRoot")
st.caption("Evidence-grounded incident investigation")
with st.sidebar.expander("Help / Getting Started", expanded=True):
    st.markdown("""
**Your first investigation**

Set `OPENAI_API_KEY` in `.env` or your environment before running.
Investigations and evaluation make model API calls.

1. **Choose or enter an incident.** Existing Evaluation Incident uses local
   evidence. Live Incident queries your configured live sources. New Incident
   remains a demo with no connected operational evidence.
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
- **Tool Call:** one query of local or live logs, metrics, deployments, or code changes.
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
Live results are saved to `experiments/results/live/<runtime-id>-agent.json`.
""")
mode = st.sidebar.selectbox(
    "Mode", ["Existing Evaluation Incident", "New Incident", "Live Incident"]
)
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
elif mode == "New Incident":
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
else:
    st.info(
        "Live Incident uses the source settings in your environment or .env file. "
        "Set TRACEROOT_LOKI_BASE_URL, TRACEROOT_PROMETHEUS_BASE_URL, "
        "TRACEROOT_GITHUB_REPO, and TRACEROOT_GITHUB_SERVICE before investigating."
    )
    if "live_start_time" not in st.session_state:
        st.session_state["live_start_time"] = datetime.now(UTC).isoformat(
            timespec="seconds"
        )
    with st.form("live_incident"):
        title = st.text_input("Title", key="live_title")
        description = st.text_area("Description", key="live_description")
        start_time = st.text_input(
            "Start time (ISO 8601, include timezone)", key="live_start_time"
        )
        services = st.text_input(
            "Suspected services (optional, comma-separated)", key="live_services"
        )
        start = st.form_submit_button("Start Investigation", type="primary")
    if start:
        try:
            incident = new_live_incident(title, description, start_time, services)
        except ValueError:
            st.error(
                "Enter a title, description, and valid ISO 8601 start time with a timezone."
            )

context = (mode, str(incident_path))
if st.session_state.get("context") != context or start:
    st.session_state.pop("completed", None)
    st.session_state.pop("evaluation", None)
    st.session_state.pop("completed_trace_path", None)
    st.session_state["context"] = context

live_config = None
if start and incident is not None and mode == "Live Incident":
    try:
        live_config = load_live_evidence_config()
    except ValidationError as exc:
        invalid_fields = ", ".join(
            str(error["loc"][0])
            for error in exc.errors(include_input=False, include_context=False)
        )
        st.error(
            f"Live configuration is missing or invalid: {invalid_fields}. "
            "Check the TRACEROOT_* settings in .env or your environment."
        )
        incident = None

if start and incident is not None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.error(
            "Set OPENAI_API_KEY in your environment or .env file before investigating."
        )
    else:
        try:
            with st.spinner("Investigating…"):
                if mode == "Live Incident":
                    record, trace_path = run_live_investigation(
                        incident, live_config, int(budget)
                    )
                    st.session_state["completed_trace_path"] = trace_path
                else:
                    record = run_investigation(
                        incident, int(budget), is_new=mode == "New Incident"
                    )
            st.session_state["completed"] = (incident, record, incident_path)
        except FileNotFoundError:
            if mode == "Live Incident":
                st.error(
                    "Live investigation files could not be accessed. Check the result directory."
                )
            else:
                st.error(
                    "Incident evidence files are missing. Check the incident dataset."
                )
        except OpenAIError:
            st.error(
                "The LLM request failed. Check your API credentials, connectivity, and model configuration, then retry."
            )
        except HTTPError:
            st.error(
                "The evidence request failed. Check source settings, access, and connectivity, then retry."
            )
        except Exception as exc:
            logger.exception("Investigation failed")
            if mode == "Live Incident":
                if isinstance(exc, ValueError) and str(exc) == (
                    "No evidence gathered for RCA generation."
                ):
                    st.error(
                        "No evidence was gathered for this incident. Check the incident "
                        "time, service leads, and live source configuration."
                    )
                else:
                    st.error(
                        "Live investigation failed. Check live source and model configuration, then retry."
                    )
            else:
                st.error(
                    "Investigation failed. Check the dataset and model configuration, then retry."
                )

if completed := st.session_state.get("completed"):
    completed_incident, record, frozen_path = completed
    if mode != "Existing Evaluation Incident":
        st.subheader("Incident")
        st.write("Title:", completed_incident.title)
        st.write("Description:", completed_incident.description)
        st.write("Start time:", completed_incident.start_time.isoformat())
        st.write(
            "Suspected services:",
            ", ".join(completed_incident.suspected_services) or "None",
        )
    st.write("Incident ID:", record.incident_id)
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
    if trace_path := st.session_state.get("completed_trace_path"):
        st.write("Trace saved to:", str(trace_path))

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
