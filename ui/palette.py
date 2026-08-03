GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
NEUTRAL = "#6b6b6b"

STATUS_STYLES = {
    "verified_remediated": ("✓", GOOD),
    "verified_divergent": ("✗", CRITICAL),
    "unverifiable": ("—", NEUTRAL),
    "PASS": ("✓", GOOD),
    "FAIL": ("✗", CRITICAL),
}


def status_badge(status: str) -> tuple[str, str]:
    """Return (icon, hex_color) for a status string.

    Raises KeyError for an unknown status — callers should only pass
    values that already come from verify.py's classification or
    audit_log's result field, both closed vocabularies.
    """
    return STATUS_STYLES[status]
