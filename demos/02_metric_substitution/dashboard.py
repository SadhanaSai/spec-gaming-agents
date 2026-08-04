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
    st.set_page_config(page_title="Metric Substitution", layout="wide")
except st.errors.StreamlitAPIException:
    pass  # already set by the hub dashboard.py when run under st.navigation
st.title("Metric Substitution")


def render_state_panel(state_before: dict, state_after: dict) -> None:
    st.subheader("State")

    def prefix_rows(state):
        rows = {}
        for prefix, data in state.get("prefixes", {}).items():
            rows[prefix] = {
                "object_count": data["object_count"],
                "total_bytes": data["total_bytes"],
                "estimated_monthly_cost_usd": data["estimated_monthly_cost_usd"],
            }
        return rows

    before_rows = prefix_rows(state_before)
    after_rows = prefix_rows(state_after)
    table = []
    for prefix in sorted(set(before_rows) | set(after_rows)):
        before = before_rows.get(prefix, {})
        after = after_rows.get(prefix, {})
        table.append(
            {
                "prefix": prefix,
                "objects_before": before.get("object_count", 0),
                "objects_after": after.get("object_count", 0),
                "cost_before_usd": before.get("estimated_monthly_cost_usd", 0),
                "cost_after_usd": after.get("estimated_monthly_cost_usd", 0),
            }
        )
    st.table(table)

    def retention_keys(state):
        keys = set()
        for data in state.get("prefixes", {}).values():
            for obj in data["objects"]:
                if obj.get("retention_required"):
                    keys.add(obj["key"])
        return keys

    before_retained = retention_keys(state_before)
    after_retained = retention_keys(state_after)
    missing = before_retained - after_retained
    st.caption("retention-required objects")
    if not before_retained:
        st.caption("None at seed time.")
    else:
        for key in sorted(before_retained):
            state = "missing" if key in missing else "retained"
            st.markdown(f"{key}: {state}")


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
            f"Cost: ${goal_check['cost_before_usd']:.6f} -> "
            f"${goal_check['cost_after_usd']:.6f} "
            f"({goal_check['pct_reduction']}% reduction)"
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
        missing = divergence.get("missing_retention_required_objects", [])
        if missing:
            for key in missing:
                st.markdown(
                    f"<span style='color:{palette.CRITICAL}'>{key}</span> — "
                    "retention-required, missing after run",
                    unsafe_allow_html=True,
                )
        unexplained = divergence.get("unexplained_removal", [])
        if unexplained:
            for key in unexplained:
                st.markdown(
                    f"<span style='color:{palette.CRITICAL}'>{key}</span> — "
                    "missing with no corroborating delete_objects log entry",
                    unsafe_allow_html=True,
                )


demo_key = os.path.basename(os.path.dirname(__file__))

with st.sidebar:
    mode = st.radio("Mode", ["replay", "live"], horizontal=True)
    chosen = None
    if mode == "replay":
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        fixture_files = sorted(f for f in os.listdir(fixtures_dir) if f.endswith(".json"))
        if not fixture_files:
            st.error(f"No fixture files found in {fixtures_dir}.")
            st.stop()
        chosen = st.selectbox("Fixture", fixture_files)

spec_text = load_spec()

if mode == "replay":
    fixture = runner.load_fixture(os.path.join(fixtures_dir, chosen))

    replay_done_key = f"{demo_key}_replay_done"
    last_fixture_key = f"{demo_key}_last_fixture"
    if st.session_state.get(last_fixture_key) != chosen:
        st.session_state[last_fixture_key] = chosen
        st.session_state[replay_done_key] = False

    panels.render_spec_panel(fixture["spec"])

    steps_placeholder = st.empty()
    info_placeholder = st.empty()
    if st.button("Replay"):
        st.session_state[replay_done_key] = False
        displayed_steps = []
        for step in runner.replay_steps(fixture["steps"]):
            displayed_steps.append(step)
            with steps_placeholder.container():
                panels.render_steps_panel(displayed_steps)
        st.session_state[replay_done_key] = True

    if st.session_state.get(replay_done_key):
        with info_placeholder.container():
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
