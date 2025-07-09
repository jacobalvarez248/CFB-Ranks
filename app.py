import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import streamlit.components.v1 as components

# Detect mobile user agent using streamlit-user-agents
# Requires: pip install streamlit-user-agents
from streamlit_user_agents import detect
user_agent = detect()
def is_mobile():
    return user_agent.is_mobile or st.sidebar.session_state.get("FORCE_MOBILE", False)

# --- Load Data ---
# Helper to load Excel sheets via xlwings or pandas/openpyxl
def load_sheet(data_path: Path, sheet_name: str, header: int = 1) -> pd.DataFrame:
    try:
        import xlwings as xw
        wb = xw.Book(data_path)
        sht = wb.sheets[sheet_name]
        df = (
            sht.range("A1")
               .options(pd.DataFrame, header=header, index=False, expand="table")
               .value
        )
    except ImportError:
        df = pd.read_excel(
            data_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            header=header
        )
    return df

# Force mobile toggle (hidden if auto-detected)
default_mobile = user_agent.is_mobile
st.sidebar.checkbox("Mobile View", default_mobile, key="FORCE_MOBILE")

# Use collapsed sidebar if mobile
if is_mobile():
    st.set_page_config(
        page_title="CFB 2025 Preview",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
else:
    st.set_page_config(
        page_title="CFB 2025 Preview",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

st.title("🎯 College Football 2025 Pre-Season Preview")

# --- Data Cleaning & Renaming ---
# Normalize Conference names in df_expected to match logo sheet (drop hyphens & uppercase)
# ... (rest of your original code remains unchanged)
