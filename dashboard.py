import glob
import os
import re

import streamlit as st

st.set_page_config(page_title="Spec Gaming Agents", layout="wide")

_ROOT = os.path.dirname(__file__)


def discover_demo_pages():
    """
    Build the nav page list by scanning demos/*/ instead of hardcoding one
    st.Page per demo — a new demos/0N_name/ folder with a dashboard.py and
    README.md shows up here with no edits to this file.
    """
    pages = []
    for demo_dir in sorted(glob.glob(os.path.join(_ROOT, "demos", "*"))):
        dashboard_path = os.path.join(demo_dir, "dashboard.py")
        if not os.path.isfile(dashboard_path):
            continue

        slug = os.path.basename(demo_dir)
        title = slug
        readme_path = os.path.join(demo_dir, "README.md")
        if os.path.isfile(readme_path):
            with open(readme_path) as f:
                first_line = f.readline().strip()
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()

        url_path = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        pages.append(st.Page(dashboard_path, title=title, url_path=url_path))
    return pages


pages = discover_demo_pages()
if not pages:
    st.error(f"No demos found under {os.path.join(_ROOT, 'demos')}.")
    st.stop()

st.navigation(pages).run()
