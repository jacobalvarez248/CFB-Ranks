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
df_expected = df_expected.merge(
    logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]],
    on="Team", how="left"
)

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

    # Column headers mapping
    mobile_map = {
        "Preseason Rank": "Rank", "Team": "Team", "Power Rating": "Pwr. Rtg.",
        "Projected Overall Wins": "Proj. Wins", "Projected Overall Losses": "Proj. Losses",
        "OVER/UNDER Pick": "OVER/ UNDER", "Average Game Quality": "Avg. Game Qty",
        "Schedule Difficulty Rating": "Sched. Diff."
    }
    mobile_cols = list(mobile_map.keys())

    # Styles
    if is_mobile():
        cols = [c for c in mobile_cols if c in df.columns]
        headers = [mobile_map[c] for c in cols]
        wrapper = (
            "max-width:100vw; height:60vh; margin:0 -16px; "
            "overflow-x:auto; overflow-y:auto;"
        )
        table_style = (
            "width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
        )
        th_base = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:10;'
        )
        td_font = "font-size:13px; white-space:nowrap;"
    else:
        cols = df.columns.tolist()
        headers = cols
        wrapper = (
            "max-width:100%; height:70vh; overflow-x:auto; overflow-y:auto;"
        )
        table_style = "width:100%; border-collapse:collapse;"
        th_base = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:5;'
        )
        td_font = "white-space:nowrap; font-size:15px;"

    # Build HTML
    html = [f"<div style='{wrapper}'>", f"<table style='{table_style}'>", '<thead><tr>']
    for h, c in zip(headers, cols):
        th_style = th_base
        if c == "Team":
            th_style += " left:0; z-index:12;"
        html.append(f"<th style='{th_style}'>{h}</th>")
    html.append('</tr></thead><tbody>')

    # Rows
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    for _, row in df.iterrows():
        html.append('<tr>')
        for c in cols:
            val = row[c]
            style = f"border:1px solid #ddd; padding:8px; text-align:center; {td_font}"
            cell = val
            if c == "Team":
                logo = row.get("Logo URL")
                if isinstance(logo, str) and logo.startswith("http"):
                    img = f'<img src="{logo}" width="24" style="margin-right:8px;"/>'
                    cell = f'<div style="display:flex;align-items:center;">{img}{val}</div>' if not is_mobile() else img
                else:
                    cell = "" if is_mobile() else val
            html.append(f"<td style='{style}'>{cell}</td>")
        html.append('</tr>')
    html.append('</tbody></table></div>')

    st.markdown(''.join(html), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # Existing code follows...
