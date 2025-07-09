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
FORCE_MOBILE = st.sidebar.checkbox("Force mobile view", False)
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

    # Columns to display
    mobile_cols = [
        "Preseason Rank", 
        "Team",  # Logo only
        "Vegas Win Total",
        "Projected Overall Wins",
        "Projected Overall Losses",
        "OVER/UNDER Pick",
        "Average Game Quality",
        "Schedule Difficulty Rating",
    ]
    if is_mobile():
        cols_rank = [c for c in mobile_cols if c in df.columns]
        table_style = "width:100%; border-collapse:collapse; table-layout:fixed;"
    else:
        cols_rank = (
            df.columns.tolist()[: df.columns.tolist().index("Schedule Difficulty Rating") + 1]
            if "Schedule Difficulty Rating" in df.columns else df.columns.tolist()
        )
        table_style = "width:100%; border-collapse:collapse;"

    html = [
        '<div style="max-height:600px; overflow-y:auto;">',
        f'<table style="{table_style}">',
        '<thead><tr>'
    ]
    for c in cols_rank:
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            th += " white-space:nowrap; min-width:48px; max-width:48px;"
        html.append(f"<th style='{th}'>{c if c != 'Team' else ''}</th>")
    html.append("</tr></thead><tbody>")

    # For coloring
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    for _, row in df.iterrows():
        html.append("<tr>")
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
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
                # existing branches
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
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()

    # --- Side-by-side Table and Scatterplot ---
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
            if c == "Conference":
                th += " white-space:nowrap; min-width:150px;"
            html_sum.append(f"<th style='{th}'>{c}</th>")
        html_sum.append("</tr></thead><tbody>")

        for _, row in summary.iterrows():
            html_sum.append("<tr>")
            for c in cols_sum:
                v = row[c]
                td = 'border:1px solid #ddd; padding:8px; text-align:center;'
                if c == "Conference":
                    logo = row.get("Logo URL")
                    if not (isinstance(logo, str) and logo.startswith("http")) or logo.strip() == "":
                        logo = "https://png.pngtree.com/png-vector/20230115/ourmid/pngtree-american-football-nfl-rugby-ball-illustration-clipart-design-png-image_6564471.png"
                    cell = (
                        f'<div style="display:flex;align-items:center;">'
                        f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                    )


                elif c in ["Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]:
                    mn, mx = (
                        (pr_min, pr_max) if c == "Avg. Power Rating" else
                        (agq_min, agq_max) if c == "Avg. Game Quality" else
                        (sdr_min, sdr_max)
                    )
                    t = (v - mn) / (mx - mn) if mx > mn else 0
                    if c == "Avg. Schedule Difficulty":
                        t = 1 - t
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'white' if t>0.5 else 'black'};"
                    cell = f"{v:.1f}"
                else:
                    cell = v
                html_sum.append(f"<td style='{td}'>{cell}</td>")
            html_sum.append("</tr>")
        html_sum.append("</tbody></table></div>")
        st.markdown("".join(html_sum), unsafe_allow_html=True)

    with right:
      st.markdown("#### Conference
