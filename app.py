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

# --- Streamlit Config ---
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

# --- Data Cleaning & Renaming ---
# Normalize Conference names in df_expected to match logo sheet (drop hyphens & uppercase)
df_expected["Conference"] = (
    df_expected["Conference"].astype(str)
    .str.strip()
    .str.replace("-", "", regex=False)
    .str.upper()
)

empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
df_expected.drop(columns=["Column1", "Column3"], inplace=True, errors='ignore')
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
# Add Preseason Rank if missing
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
# Format probabilities
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = (
        df_expected["Undefeated Probability"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
        )
    )
# Round numeric cols except ranks
drop_ranks = ["Preseason Rank", "Schedule Difficulty Rank", "Final 2024 Rank"]
numeric_cols = [c for c in df_expected.select_dtypes(include=["number"]).columns if c not in drop_ranks]
df_expected[numeric_cols] = df_expected[numeric_cols].round(1)
# Ensure types
for col in ["Preseason Rank", "Final 2024 Rank"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').fillna(0).astype(int)
for col in ["Power Rating", "Average Game Quality", "Schedule Difficulty Rating"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').round(1)

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
        # "Vegas Win Total": "Win Total",  # REMOVED
        "Power Rating": "Pwr. Rtg.",      # ADDED
        "Projected Overall Wins": "Proj. Wins",
        "Projected Overall Losses": "Proj. Losses",
        "OVER/UNDER Pick": "OVER/UNDER",
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
            "max-width:100vw; overflow-x:hidden; margin:0 -16px 0 -16px;"
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
        wrapper_style = "max-width:100%; overflow-x:auto;"
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"

    html = [
        f'<div style="{wrapper_style}">',
        f'<table style="{table_style}">',
        '<thead><tr>'
    ]
    # Use display_headers for headers, always "Team" for the team column
    for idx, (disp_col, c) in enumerate(zip(display_headers, cols_rank)):
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        # --- Freeze left columns for desktop ---
        if not is_mobile():
            # You can freeze as many columns as you want here by extending the pattern
            if c == "Preseason Rank":
                th += " left:0; z-index:3; background:#002060;" # First frozen col
            elif c == "Team":
                th += " left:60px; z-index:3; background:#002060;" # Adjust pixel value if needed
            # To freeze more, add more elifs with left:
    elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")

    # --- Data Prep for Table and Scatter ---
    summary = (
        df_expected.groupby("Conference").agg(
            **{
                "# Teams": ("Preseason Rank", "count"),
                "Avg. Power Rating": ("Power Rating", "mean"),
                "Avg. Game Quality": ("Average Game Quality", "mean"),
                "Avg. Schedule Difficulty": ("Schedule Difficulty Rating", "mean"),
            }
        ).reset_index()
    )
    summary[["Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]] = (
        summary[["Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]].round(1)
    )
    logos_conf = logos_df.copy()
    if "Image URL" in logos_conf.columns:
        logos_conf.rename(columns={"Image URL": "Logo URL"}, inplace=True)
    if "Team" in logos_conf.columns and "Conference" not in logos_conf.columns:
        logos_conf.rename(columns={"Team": "Conference"}, inplace=True)
    logos_conf["Conference"] = (
        logos_conf["Conference"]
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
    summary["Conference"] = (
        summary["Conference"]
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
    if {"Conference", "Logo URL"}.issubset(logos_conf.columns):
        summary = summary.merge(
            logos_conf[["Conference", "Logo URL"]],
            on="Conference",
            how="left"
        )

    # --- Side-by-side Table and (optional) Chart ---
    left, right = st.columns([1, 1])

    with left:
        html_sum = [
            '<div style="overflow-x:auto;">',
            '<table style="width:100%; border-collapse:collapse;">',
            '<thead><tr>'
        ]
        cols_sum = ["Conference", "# Teams", "Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]
        for c in cols_sum:
            th = (
                'border:1px solid #ddd; padding:8px; text-align:center; '
                'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
            )
            html_sum.append(f"<th style='{th}'>{c}</th>")
        html_sum.append("</tr></thead><tbody>")

        for _, row in summary.iterrows():
            html_sum.append("<tr>")
            for c in cols_sum:
                td = 'border:1px solid #ddd; padding:8px; text-align:center;'
                val = row[c]
                if c == "Conference":
                    logo = row.get("Logo URL")
                    if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                        cell = f'<div style="display:flex;align-items:center;"><img src="{logo}" width="24" style="margin-right:8px;"/>{val}</div>'
                    else:
                        cell = val
                else:
                    cell = f"{val:.1f}" if isinstance(val, float) else val
                html_sum.append(f"<td style='{td}'>{cell}</td>")
            html_sum.append("</tr>")
        html_sum.append("</tbody></table></div>")
        st.markdown("".join(html_sum), unsafe_allow_html=True)

    # (Optional: place your Altair chart or more analysis in the `with right:` block)

