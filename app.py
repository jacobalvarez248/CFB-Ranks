import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import streamlit.components.v1 as components

# Mobile detection: try to import streamlit-user-agents
try:
    from streamlit_user_agents import detect
    user_agent = detect()
    default_mobile = user_agent.is_mobile
except ImportError:
    default_mobile = False  # streamlit-user-agents not installed, default to desktop

# --- Page Config & Sidebar Mobile Toggle ---
# Set page config before any other Streamlit calls
if default_mobile:
    initial_state = "collapsed"
else:
    initial_state = "expanded"
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state=initial_state
)

# Sidebar Mobile Toggle
st.sidebar.checkbox("Mobile View", default_mobile, key="FORCE_MOBILE")

def is_mobile():
    return st.session_state.FORCE_MOBILE

# Collapse sidebar on mobile
if is_mobile():
    st.sidebar.empty()

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
if "Conference" in df_expected.columns:
    df_expected["Conference"] = (
        df_expected["Conference"].astype(str)
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
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
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = (
        df_expected["Undefeated Probability"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
        )
    )
drop_ranks = ["Preseason Rank", "Schedule Difficulty Rank"]
numeric_cols = [c for c in df_expected.select_dtypes(include=["number"]) if c not in drop_ranks]
if numeric_cols:
    df_expected[numeric_cols] = df_expected[numeric_cols].round(1)

# Sidebar Navigation
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# --- Tabs ---
if tab == "Rankings":
    st.header("📋 Rankings")
    # Display the full expected wins table
    st.dataframe(df_expected, use_container_width=True)
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # Conference-overview visuals here
    pass
elif tab == "Team Dashboards":
    st.header("🏈 Team Dashboards")
    # Team dashboard visuals here
    pass
elif tab == "Charts & Graphs":
    st.header("📊 Charts & Graphs")
    # Charts and graphs visuals here
    pass
