import streamlit as st

_CSS = """
<style>
:root {
    --border: #262a35;
    --muted: #8b909c;
}

html, body, [class*="css"] {
    font-family: -apple-system, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
}

/* page shell */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* title */
h1 {
    font-weight: 650 !important;
    letter-spacing: -0.01em;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem !important;
}

/* section headers (st.subheader) */
h3 {
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted) !important;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin-top: 2rem !important;
    margin-bottom: 0.9rem !important;
}

/* captions used as sub-labels */
[data-testid="stCaptionContainer"] {
    text-transform: uppercase;
    font-size: 0.72rem !important;
    letter-spacing: 0.06em;
    color: var(--muted) !important;
    font-weight: 600;
}

/* sidebar */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* buttons: flat, bordered, no gradient */
[data-testid="stBaseButton-secondary"], .stButton button {
    border-radius: 3px;
    border: 1px solid var(--border);
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    font-size: 0.78rem;
}

/* tables: tighter, monospace values, uppercase headers */
[data-testid="stTable"] table {
    font-size: 0.85rem;
}
[data-testid="stTable"] thead th {
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.7rem !important;
    color: var(--muted) !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-testid="stTable"] td, [data-testid="stTable"] th {
    font-family: "SF Mono", "Consolas", "Menlo", monospace;
}

/* code-styled inline markdown (step timestamps) */
code {
    font-size: 0.85em;
}

/* status pill badges */
.sg-badge {
    display: inline-block;
    padding: 0.12rem 0.55rem;
    border-radius: 3px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border: 1px solid currentColor;
}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
