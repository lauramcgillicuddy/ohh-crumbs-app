"""Lightweight Streamlit entry point for the Profitability Audit page.

Runs just the audit (not the full 30-module app), so it boots with a small
dependency set — no WeasyPrint/Poppler. Points at the SQLite DB that
`sync_cli.py` populated unless DATABASE_URL is already set.

    streamlit run audit_app.py
"""
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(__file__).with_name('ohh_crumbs.db')}")

import streamlit as st

st.set_page_config(page_title="Ohh Crumbs — Profitability Audit",
                   page_icon="🔍", layout="wide")

from database import init_db
init_db()

import audit
audit.show_audit()
