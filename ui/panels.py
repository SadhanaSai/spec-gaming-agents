import streamlit as st

from ui import palette


def render_spec_panel(spec_text: str) -> None:
    st.subheader("📋 Spec")
    st.text(spec_text)


def render_steps_panel(steps: list[dict]) -> None:
    st.subheader("🔄 Agent Steps")
    if not steps:
        st.caption("No steps yet.")
        return
    for step in steps:
        timestamp = step["timestamp"]
        if step["type"] == "reasoning":
            st.markdown(f"`[{timestamp}s]` 💭 {step['content']}")
        elif step["type"] == "tool_call":
            st.markdown(
                f"`[{timestamp}s]` 🔧 **{step['tool']}**({step['input']}) "
                f"→ `{step['output']}`"
            )


def render_state_panel(state_before: dict, state_after: dict) -> None:
    st.subheader("📦 State")

    before_by_id = {f["finding_id"]: f for f in state_before.get("findings", [])}
    after_by_id = {f["finding_id"]: f for f in state_after.get("findings", [])}
    rows = []
    for finding_id in sorted(set(before_by_id) | set(after_by_id)):
        before = before_by_id.get(finding_id, {})
        after = after_by_id.get(finding_id, {})
        rows.append(
            {
                "finding_id": finding_id,
                "severity": after.get("severity", before.get("severity", "")),
                "status_before": before.get("status", ""),
                "status_after": after.get("status", ""),
            }
        )
    st.table(rows)

    for key, value in state_after.items():
        if key == "findings":
            continue
        if isinstance(value, dict) and value and all(
            isinstance(v, bool) for v in value.values()
        ):
            st.caption(key)
            cols = st.columns(len(value))
            for col, (flag_name, flag_value) in zip(cols, value.items()):
                icon = "✅" if flag_value else "❌"
                col.markdown(f"{icon} {flag_name}")


def render_divergence_panel(audit_log: dict, divergence: dict) -> None:
    st.subheader("⚖️ Audit vs. Divergence")
    col1, col2 = st.columns(2)

    with col1:
        st.caption("Audit Log (spec-literal check)")
        icon, color = palette.status_badge(audit_log["result"])
        st.markdown(
            f"<span style='color:{color}; font-weight:bold'>"
            f"{icon} {audit_log['result']}</span> — {audit_log['check']}",
            unsafe_allow_html=True,
        )
        st.caption(f"Open Critical/High: {audit_log['open_critical_high_count']}")

    with col2:
        st.caption("Divergence (intent-verified check)")
        detected = divergence["detected"]
        label = "DIVERGENCE DETECTED" if detected else "NO DIVERGENCE"
        color = palette.CRITICAL if detected else palette.GOOD
        st.markdown(
            f"<span style='color:{color}; font-weight:bold'>{label}</span>",
            unsafe_allow_html=True,
        )
        for finding_id, result in divergence["findings"].items():
            icon, color = palette.status_badge(result["status"])
            st.markdown(
                f"<span style='color:{color}'>{icon} {finding_id}: "
                f"{result['status']}</span> — {result['detail']}",
                unsafe_allow_html=True,
            )
