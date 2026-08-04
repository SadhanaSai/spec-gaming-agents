GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
NEUTRAL = "#6b6b6b"

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
