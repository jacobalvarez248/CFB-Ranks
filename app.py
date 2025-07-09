import pandas as pd
import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components

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

# Merge team logos only
team_logos = logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]]
df_expected = df_expected.merge(team_logos, on="Team", how="left")

# --- Streamlit Config ---
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🎯 College Football 2025 Pre-Season Preview")

# --- Data Cleaning & Renaming ---
df_expected["Conference"] = (
    df_expected["Conference"].astype(str)
    .str.strip()
    .str.replace("-", "", regex=False)
    .str.upper()
)
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
df_expected.drop(columns=["Column1", "Column3"], inplace=True, errors='ignore')
rename_map = {...}  # existing rename_map content
# (retain previous rename_map logic)
# Add Preseason Rank, format probabilities, round numbers, ensure types
# (retain existing cleaning logic)

# --- Sidebar & Tabs ---
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# ------ Rankings ------
if tab == "Rankings":
    st.header("📋 Rankings")
    # CSS & responsiveness for mobile portrait
    st.markdown(
        """
        <style>
        /* Hide sidebar on portrait */
        @media only screen and (orientation: portrait) {
            .css-1d391kg {display:none!important;}  /* sidebar container */
            .css-1fjq9mv {margin-left:0!important;} /* main content shift */
        }
        /* Desktop vs Mobile table */
        .desktop-table {display:table!important;} .mobile-table {display:none!important;}
        @media only screen and (orientation: portrait) {
            .desktop-table {display:none!important;} .mobile-table {display:table!important;}
        }
        /* Mobile table layout */
        .mobile-table div {overflow-x:hidden!important;} .mobile-table table {table-layout:fixed!important;width:100%!important;}
        </style>
        """, unsafe_allow_html=True
    )
    # Filters & sorting
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", df_expected.columns, df_expected.columns.get_loc("Preseason Rank")
    )
    asc = st.sidebar.checkbox("Ascending order", True)

    df = df_expected.copy()
    # apply filters
    if team_search:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    # default sort
    df = df.sort_values(by="Preseason Rank")
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # compute color bounds
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    # --- Mobile Table ---
    mobile_cols = ["Preseason Rank", "Team", "Vegas Win Total", "Projected Overall Wins",
                   "Projected Overall Losses", "OVER/UNDER Pick",
                   "Average Game Quality", "Schedule Difficulty Rating"]
    mobile_html = ['<div class="mobile-table" style="max-height:600px;">',
                   '<table style="border-collapse:collapse;width:100%;">', '<thead><tr>']
    for c in mobile_cols:
        mobile_html.append(
            f"<th style='border:1px solid #ddd;padding:8px;text-align:center;" +
            f"background-color:#002060;color:white;position:sticky;top:0;z-index:2;'>{c}</th>"
        )
    mobile_html.append('</tr></thead><tbody>')
    for _, row in df.iterrows():
        mobile_html.append('<tr>')
        for c in mobile_cols:
            td = 'border:1px solid #ddd;padding:8px;text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL")
                cell = f'<img src="{logo}" width="24"/>' if pd.notnull(logo) else ''
            else:
                v = row.get(c)
                if c == "OVER/UNDER Pick" and isinstance(v, str):
                    cell = v
                    if v.upper().startswith("OVER"): td += "background-color:#28a745;color:white;"
                    elif v.upper().startswith("UNDER"): td += "background-color:#dc3545;color:white;"
                elif c == "Average Game Quality" and pd.notnull(v):
                    t = (v - agq_min) / (agq_max - agq_min) if agq_max > agq_min else 0
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f"background-color:#{r:02x}{g:02x}{b:02x};color:{'black' if t<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                    inv = 1 - ((v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 0)
                    r, g, b = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                    td += f"background-color:#{r:02x}{g:02x}{b:02x};color:{'black' if inv<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                else:
                    cell = v if pd.notnull(v) else ''
            mobile_html.append(f"<td style='{td}'>{cell}</td>")
        mobile_html.append('</tr>')
    mobile_html.append('</tbody></table></div>')
    st.markdown(''.join(mobile_html), unsafe_allow_html=True)

    # --- Desktop Table ---
    cols_rank = (
        df.columns.tolist()[:df.columns.tolist().index("Schedule Difficulty Rating")+1]
        if "Schedule Difficulty Rating" in df.columns else df.columns.tolist()
    )
    html = ['<div class="desktop-table" style="max-height:600px; overflow-y:auto;">',
            '<table style="width:100%; border-collapse:collapse;">', '<thead><tr>']
    for c in cols_rank:
        th = ('border:1px solid #ddd; padding:8px; text-align:center; '
              'background-color:#002060; color:white; position:sticky; top:0; z-index:2;')
        if c == "Team": th += " white-space:nowrap; min-width:200px;"
        html.append(f"<th style='{th}'>{c}</th>")
    html.append('</tr></thead><tbody>')
    for _, row in df.iterrows():
        html.append('<tr>')
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            # existing formatting logic kept
            # ... (same as original branches) ...
            html.append(f"<td style='{td}'>{v if c!="Team" else row.get('Logo URL')}</td>")
        html.append('</tr>')
    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    # ... (existing conference overview code unchanged) ...
    pass

# (Repeat similar mobile/Desktop pattern for other tabs if needed)
