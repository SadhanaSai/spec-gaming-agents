GOOD = "#3fbf5e"
CRITICAL = "#e5484d"
NEUTRAL = "#9a9fac"

STATUS_COLORS = {
    "verified_remediated": GOOD,
    "verified_divergent": CRITICAL,
    "unverifiable": NEUTRAL,
    "resolved_without_log_entry": CRITICAL,
    "PASS": GOOD,
    "FAIL": CRITICAL,
}


def status_color(status: str) -> str:
    """Return a hex color for a status string.

    Raises KeyError for an unknown status — callers should only pass
    values that already come from verify.py's classification or
    goal_check's result field, both closed vocabularies.
    """
    return STATUS_COLORS[status]


def badge_html(label: str, color: str) -> str:
    """Render a status value as a bordered pill badge instead of bare colored text."""
    return f"<span class='sg-badge' style='color:{color}'>{label}</span>"
