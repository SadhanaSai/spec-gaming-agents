import os
import sys
import time

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agent import build_react_agent, load_spec, run_agent
from run import capture_state
import verify
from ui import palette, panels, runner

try:
    st.set_page_config(page_title="Demo 4 — Literal Interpretation", layout="wide")
except st.errors.StreamlitAPIException:
    pass  # already set by the hub dashboard.py when run under st.navigation
st.title("Demo 4 — Literal Interpretation")


def render_state_panel(state_before: dict, state_after: dict) -> None:
    st.subheader("State")

    before_active = {obj["key"] for obj in state_before.get("active_objects", [])}
    after_active = {obj["key"] for obj in state_after.get("active_objects", [])}
    scheduled_prefixes = {
        job["prefix"] for job in state_after.get("scheduled_jobs", [])
    }

    rows = []
    for key in sorted(before_active):
        still_active = key in after_active
        if still_active:
            status = "active"
        else:
            pending_key = f".pending-cleanup/{key}"
            scheduled = any(pending_key.startswith(p) for p in scheduled_prefixes)
            status = "relocated_and_scheduled" if scheduled else "relocated"
        rows.append({"key": key, "status": status})
    st.table(rows)

    st.caption("scheduled_jobs")
    job_rows = [
        {
            "bucket": job["bucket"],
            "prefix": job["prefix"],
            "action": job["action"],
            "execute_at": job["execute_at"],
        }
        for job in state_after.get("scheduled_jobs", [])
    ]
    if job_rows:
        st.table(job_rows)
    else:
        st.caption("None.")


def render_divergence_panel(goal_check: dict, divergence: dict) -> None:
    st.subheader("Goal Check vs. Divergence")
    col1, col2 = st.columns(2)

    with col1:
        st.caption("Goal Check (spec-literal check)")
        color = palette.status_color(goal_check["result"])
        st.markdown(
            f"<span style='color:{color}; font-weight:bold'>"
            f"{goal_check['result']}</span> — {goal_check['check']}",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Active bytes: {goal_check['active_bytes_before']} -> "
            f"{goal_check['active_bytes_after']} "
            f"({goal_check['drop_fraction'] * 100:.1f}% drop)"
        )

    with col2:
        st.caption("Divergence (intent-verified check)")
        detected = divergence["detected"]
        label = "DIVERGENCE DETECTED" if detected else "NO DIVERGENCE"
        color = palette.CRITICAL if detected else palette.GOOD
        st.markdown(
            f"<span style='color:{color}; font-weight:bold'>{label}</span>",
            unsafe_allow_html=True,
        )
        st.caption(divergence["summary"])
        for key, result in divergence["files"].items():
            diverged = result["diverged"]
            item_color = palette.CRITICAL if diverged else palette.GOOD
            st.markdown(
                f"<span style='color:{item_color}'>{key}: "
                f"{result['status']}</span> — {result['detail']}",
                unsafe_allow_html=True,
            )


mode = st.radio("Mode", ["replay", "live"], horizontal=True)

spec_text = load_spec()

if mode == "replay":
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    fixture_files = sorted(f for f in os.listdir(fixtures_dir) if f.endswith(".json"))
    if not fixture_files:
        st.error(f"No fixture files found in {fixtures_dir}.")
        st.stop()
    chosen = st.selectbox("Fixture", fixture_files)
    fixture = runner.load_fixture(os.path.join(fixtures_dir, chosen))

    panels.render_spec_panel(fixture["spec"])

    steps_placeholder = st.empty()
    if st.button("Replay"):
        displayed_steps = []
        for step in runner.replay_steps(fixture["steps"]):
            displayed_steps.append(step)
            with steps_placeholder.container():
                panels.render_steps_panel(displayed_steps)

    render_state_panel(fixture["state_before"], fixture["state_after"])
    panels.render_audit_log_panel(fixture["audit_log"])
    render_divergence_panel(fixture["goal_check"], fixture["divergence"])

elif mode == "live":
    panels.render_spec_panel(spec_text)

    steps_placeholder = st.empty()
    if st.button("Run Agent"):
        state_before = capture_state()
        agent = build_react_agent()
        messages = [HumanMessage(content=spec_text)]

        displayed_steps = []
        pending_calls = {}
        seen = 0
        start = time.monotonic()

        for state in run_agent(agent, messages):
            new_messages = state["messages"][seen:]
            seen = len(state["messages"])
            elapsed = round(time.monotonic() - start, 1)

            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    if msg.content:
                        displayed_steps.append(
                            {"timestamp": elapsed, "type": "reasoning", "content": msg.content}
                        )
                    if msg.tool_calls:
                        for call in msg.tool_calls:
                            pending_calls[call["id"]] = {
                                "timestamp": elapsed,
                                "tool": call["name"],
                                "input": call["args"],
                            }
                elif isinstance(msg, ToolMessage):
                    call = pending_calls.pop(msg.tool_call_id, None)
                    if call is not None:
                        displayed_steps.append(
                            {
                                "timestamp": call["timestamp"],
                                "type": "tool_call",
                                "tool": call["tool"],
                                "input": call["input"],
                                "output": msg.content,
                            }
                        )

            with steps_placeholder.container():
                panels.render_steps_panel(displayed_steps)

        state_after = capture_state()
        intent = verify.load_json("intent.json")
        report = verify.build_divergence_report(intent, state_before, state_after, displayed_steps)

        render_state_panel(state_before, state_after)
        panels.render_audit_log_panel(report["audit_log"])
        render_divergence_panel(report["goal_check"], report["divergence"])
