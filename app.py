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
# Trim whitespace on team names to ensure clean merge
logos_df["Team"] = logos_df["Team"].str.strip()
df_expected["Team"] = df_expected["Team"].str.strip()
# Rename Image URL -> Logo URL for consistency
if "Image URL" in logos_df.columns:
    logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)

# Prepare separate team logos and conference logos
team_logos = logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]].copy()
# Merge team logos into df_expected
# (so conference-logo entries in logos_df won't mix into team tables)
df_expected = df_expected.merge(team_logos, on="Team", how="left")

# --- Data Cleaning & Renaming ---
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
    "Final 2024 Rank": "Final 2024 Rank",
    "Final 2022 Rank": "Final 2024 Rank",
}
df_expected.rename(columns=rename_map, inplace=True)
import streamlit.components.v1 as components

# Only call this ONCE at the top, never inside a function or repeatedly
FORCE_MOBILE = st.sidebar.checkbox("Mobile View", False)
def is_mobile():
    return FORCE_MOBILE

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
    df = df.sort_values(by="Preseason Rank")
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # --- Rankings Table Setup ---
    # Short column headers for mobile
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
    mobile_cols = list(mobile_header_map.keys())

    if is_mobile():
        cols_rank = [c for c in mobile_cols if c in df.columns]
        display_headers = [mobile_header_map[c] for c in cols_rank]
        table_style = (
            "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; "
            "font-size:13px;"
        )
        wrapper_style = (
            "max-width:100vw; max-height:70vh; overflow-x:hidden; overflow-y:auto; margin:0 -16px 0 -16px;"
        )
        header_font = "font-size:13px; white-space:normal;"
        cell_font = "font-size:13px; white-space:nowrap;"
    else:
        cols_rank = (
            df.columns.tolist()[: df.columns.tolist().index("Schedule Difficulty Rating") + 1]
            if "Schedule Difficulty Rating" in df.columns else df.columns.tolist()
        )
        display_headers = [c if c != "Team" else "Team" for c in cols_rank]
        table_style = "width:100%; border-collapse:collapse;"
        wrapper_style = (
            "max-width:100vw; max-height:70vh; overflow-x:hidden; overflow-y:auto; margin:0 -16px 0 -16px;"
        )
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"

    html = [
        f'<div style="{wrapper_style}">',
        f'<table style="{table_style}">',
        '<thead><tr>'
    ]
    # Use display_headers for headers, always "Team" for the team column
    for disp_col, c in zip(display_headers, cols_rank):
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            if is_mobile():
                th += " white-space:nowrap; min-width:48px; max-width:48px;"  # tight for logo
            else:
                th += " white-space:nowrap; min-width:180px; max-width:280px;"  # much wider for desktop, no wrap
        else:
            th += " white-space:nowrap;"
        th += header_font
        html.append(f"<th style='{th}'>{disp_col}</th>")
    html.append("</tr></thead><tbody>")

    # For coloring (same as before)
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max() if "Power Rating" in df.columns else (0, 1)
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max() if "Average Game Quality" in df.columns else (0, 1)
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max() if "Schedule Difficulty Rating" in df.columns else (0, 1)

    for _, row in df.iterrows():
        html.append("<tr>")
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            td += cell_font
            cell = v
            if c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                    if is_mobile():
                        cell = f'<img src="{logo}" width="32" style="margin:0 auto; display:block;"/>'
                    else:
                        cell = (
                            f'<div style="display:flex;align-items:center;">'
                            f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                        )
                else:
                    cell = "" if is_mobile() else v
            else:
                # (conditional formatting as before)
                if c == "OVER/UNDER Pick" and isinstance(v, str):
                    if v.upper().startswith("OVER"): td += " background-color:#28a745; color:white;"
                    elif v.upper().startswith("UNDER"): td += " background-color:#dc3545; color:white;"
                elif c == "Power Rating" and pd.notnull(v):
                    t = (v - pr_min) / (pr_max - pr_min) if pr_max > pr_min else 0
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                elif c == "Average Game Quality" and pd.notnull(v):
                    t = (v - agq_min) / (agq_max - agq_min) if agq_max > agq_min else 0
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                    inv = 1 - ((v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 0)
                    r, g, b = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                else:
                    cell = v

            html.append(f"<td style='{td}'>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    st.write("This section is under construction.")
    # (Add your conference overview table/chart here)

# ------ Team Dashboards ------
elif tab == "Team Dashboards":
    st.header("🧑‍💻 Team Dashboards")
    st.write("This section is under construction.")
    # (Add your team-specific dashboard here)

# ------ Charts & Graphs ------
elif tab == "Charts & Graphs":
    st.header("📊 Charts & Graphs")
    st.write("This section is under construction.")
    # (Add your charts here)
