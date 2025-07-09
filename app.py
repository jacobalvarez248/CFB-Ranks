import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import streamlit.components.v1 as components

# Detect mobile user agent
# Requires: pip install streamlit-user-agents
from streamlit_user_agents import detect
user_agent = detect()
def is_mobile():
    return st.session_state.FORCE_MOBILE

# --- Sidebar Mobile Toggle ---
# Default to mobile view when on phone
default_mobile = user_agent.is_mobile
# Key must match session_state usage
st.sidebar.checkbox("Mobile View", default_mobile, key="FORCE_MOBILE")

# --- Page Config based on Mobile ---
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

# --- Load Data ---
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

# Data paths & loading
data_path = Path(__file__).parent / "Preseason 2025.xlsm"
df_expected = load_sheet(data_path, "Expected Wins", header=1)
logos_df = load_sheet(data_path, "Logos", header=1)

# Clean up logo columns
tlogos = logos_df.copy()
if "Image URL" in tlogos.columns:
    tlogos.rename(columns={"Image URL": "Logo URL"}, inplace=True)
for df in (tlogos, df_expected):
    if "Team" in df.columns:
        df["Team"] = df["Team"].str.strip()

team_logos = tlogos[tlogos["Team"].isin(df_expected["Team"])][["Team","Logo URL"]]
df_expected = df_expected.merge(team_logos, on="Team", how="left")

# --- Data Cleaning & Formatting ---
# Normalize conference names
if "Conference" in df_expected.columns:
    df_expected["Conference"] = (
        df_expected["Conference"].astype(str)
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
# Drop empty columns
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
# Rename map
rename_map = {
    "Column18": "Power Rating",
    "Projected Overall Record": "Projected Overall Wins",
    "Column2": "Projected Overall Losses",
    "Projected Conference Record": "Projected Conference Wins",
    "Column4": "Projected Conference Losses",
    "Pick": "OVER/UNDER Pick",
    "Column17": "Schedule Difficulty Rank",
    "xWins for Playoff Team": "Schedule Difficulty Rating",
    "Winless Probability": "Average Game Quality",
}
df_expected.rename(columns=rename_map, inplace=True)
# Add Preseason Rank if missing
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
# Format percentages
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = (
        df_expected["Undefeated Probability"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
        )
    )
# Round numeric columns
drop_ranks = ["Preseason Rank", "Schedule Difficulty Rank"]
numeric_cols = [c for c in df_expected.select_dtypes(include=["number"]) if c not in drop_ranks]
if numeric_cols:
    df_expected[numeric_cols] = df_expected[numeric_cols].round(1)

# Sidebar navigation
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# --- Rankings Tab ---
if tab == "Rankings":
    st.header("📋 Rankings")
    # ... existing rankings code here ...
    pass

# --- Conference Overviews ---
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # ... existing conference code here ...
    pass

# --- Team Dashboards ---
elif tab == "Team Dashboards":
    st.header("🏈 Team Dashboards")
    # ... team dashboard code ...
    pass

# --- Charts & Graphs ---
elif tab == "Charts & Graphs":
    st.header("📊 Charts & Graphs")
    # ... charts and graphs code ...
