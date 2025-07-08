import pandas as pd
import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 College Football 2025 Pre-Season Preview")

# Path to the Excel file at the repo root
DATA_FILE = Path(__file__).parent / "Preseason 2025.xlsm"
if not DATA_FILE.exists():
    st.error(f"Data file not found: {DATA_FILE}")
    st.stop()

# --- Load and clean Expected Wins ---
# Read with pandas + openpyxl
df_expected = pd.read_excel(
    DATA_FILE,
    sheet_name="Expected Wins",
    engine="openpyxl",
    header=1,
)
# Drop blank/placeholder columns
df_expected.drop(
    columns=[c for c in df_expected.columns if str(c).strip() == ""],
    inplace=True,
    errors='ignore'
)
for col in ["Column1", "Column3"]:
    df_expected.drop(columns=col, inplace=True, errors='ignore')
# Rename columns
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
# Preseason Rank index
df_expected.insert(0, "Preseason Rank", range(1, len(df_expected) + 1))
# Format percentages and roundings
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = df_expected["Undefeated Probability"].apply(
        lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
    )
num_cols = df_expected.select_dtypes(include=["number"]).columns.tolist()
num_cols = [c for c in num_cols if c not in ["Preseason Rank", "Schedule Difficulty Rank"]]
if num_cols:
    df_expected[num_cols] = df_expected[num_cols].round(1)
if "Schedule Difficulty Rating" in df_expected.columns:
    df_expected["Schedule Difficulty Rating"] = df_expected["Schedule Difficulty Rating"].round(1)

# --- Load Logos (optional) ---
try:
    df_images = pd.read_excel(
        DATA_FILE,
        sheet_name="Logos",
        engine="openpyxl",
        header=1,
    )
except Exception:
    df_images = pd.DataFrame()

# Sidebar navigation
tab = st.sidebar.radio(
    "Navigation", ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

if tab == "Rankings":
    st.header("📋 Rankings")
    # Sidebar filters
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox("Sort by column", df_expected.columns.tolist(), index=0)
    asc = st.sidebar.checkbox("Ascending order", value=True)
    # Prepare DataFrame copy
    df = df_expected.copy()
    if team_search and "Team" in df.columns:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=asc)
    display_df = df.copy()
    # Merge logos if available
    if not df_images.empty and {"Team","Image URL"}.issubset(df_images.columns):
        display_df = display_df.merge(df_images, on="Team", how="left")
    if "Image URL" in display_df.columns:
        display_df["Team"] = display_df.apply(
            lambda r: (
                f'<img src="{r["Image URL"]}" width="24" style="vertical-align:middle; margin-right:8px;">'
                f'{r["Team"]}'
                if pd.notnull(r["Image URL"]) else r["Team"]
            ), axis=1
        )
        display_df.drop(columns="Image URL", inplace=True, errors='ignore')
    # Render table
    st.dataframe(display_df)

elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    st.info("Coming soon: Conference overview analysis will appear here.")

elif tab == "Team Dashboards":
    st.header("📊 Team Dashboards")
    st.info("Team dashboards are not yet supported in this deployed version.")

elif tab == "Charts & Graphs":
    st.header("📈 Charts & Graphs")
    st.info("Charts & Graphs are currently not available in this deployed version.")
