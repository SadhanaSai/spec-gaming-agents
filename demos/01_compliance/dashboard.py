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
from ui import panels, runner

try:
    st.set_page_config(page_title="Demo 1 — Compliance Theater", layout="wide")
except st.errors.StreamlitAPIException:
    pass  # already set by the hub dashboard.py when run under st.navigation
st.title("Demo 1 — Compliance Theater")

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
            panels.render_state_panel(fixture["state_before"], fixture["state_after"])
            panels.render_audit_log_panel(fixture["audit_log"])
            panels.render_divergence_panel(fixture["goal_check"], fixture["divergence"])

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

        panels.render_state_panel(state_before, state_after)
        panels.render_audit_log_panel(report["audit_log"])
        panels.render_divergence_panel(report["goal_check"], report["divergence"])
