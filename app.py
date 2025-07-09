import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt

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

# --- Load Data ---
data_path = Path(__file__).parent / "Preseason 2025.xlsm"
df_expected = load_sheet(data_path, "Expected Wins", header=1)
logos_df = load_sheet(data_path, "Logos", header=1)

# Normalize logo column
logos_df["Team"] = logos_df["Team"].str.strip()
df_expected["Team"] = df_expected["Team"].str.strip()
if "Image URL" in logos_df.columns:
    logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)

# Prepare logos and merge
team_logos = logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]].copy()
df_expected = df_expected.merge(team_logos, on="Team", how="left")

# --- Streamlit Config ---
import streamlit.components.v1 as components
FORCE_MOBILE = st.sidebar.checkbox("Mobile View", False)
def is_mobile():
    return FORCE_MOBILE

# Page config
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
# Normalize, drop empty cols, rename, format
# ... (existing cleaning steps unchanged) ...

# --- Sidebar & Tabs ---
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# ------ Rankings ------
if tab == "Rankings":
    st.header("📋 Rankings")
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", df_expected.columns, df_expected.columns.get_loc("Preseason Rank")
    )
    asc = st.sidebar.checkbox("Ascending order", True)

    df = df_expected.copy()
    if team_search:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # Short headers map
    mobile_header_map = {
        "Preseason Rank": "Rank",
        "Team": "Team",
        "Power Rating": "Pwr. Rtg.",
        "Projected Overall Wins": "Proj. Wins",
        "Projected Overall Losses": "Proj. Losses",
        "OVER/UNDER Pick": "OVER/ UNDER",
        "Average Game Quality": "Avg. Game Qty",
        "Schedule Difficulty Rating": "Sched. Diff.",
    }

    if is_mobile():
        cols_rank = [c for c in mobile_header_map.keys() if c in df.columns]
        display_headers = [mobile_header_map[c] for c in cols_rank]
        table_style = (
            "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
        )
        wrapper_style = (
            "max-width:100vw; overflow-x:auto; margin:0 -16px 0 -16px;"
        )
        header_font = "font-size:13px; white-space:normal;"
        cell_font = "font-size:13px; white-space:nowrap;"
    else:
        cols_rank = (
            df.columns.tolist()[: df.columns.tolist().index("Schedule Difficulty Rating") + 1]
            if "Schedule Difficulty Rating" in df.columns else df.columns.tolist()
        )
        display_headers = [c for c in cols_rank]
        table_style = "width:100%; border-collapse:collapse;"
        wrapper_style = "max-width:100%; overflow-x:auto;"
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"

    html = [f'<div style="{wrapper_style}">', f'<table style="{table_style}">', '<thead><tr>']
    for disp_col, c in zip(display_headers, cols_rank):
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0;'
        )
        if c == "Team":
            th_style += ' left:0; z-index:3;'
        else:
            th_style += ' z-index:2;'
        th_style += header_font
        html.append(f"<th style='{th_style}'>{disp_col}</th>")
    html.append('</tr></thead><tbody>')

    # ... (row rendering unchanged) ...

    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")

    # Existing summary table code already uses position:sticky for headers
    # So headers will remain frozen here as well
    # ... (rest of code unchanged) ...
