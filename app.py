
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
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🎯 College Football 2025 Pre-Season Preview")

st.markdown("""
<style>
  .responsive-table { 
    overflow-x: hidden; 
    width: 100%; 
    table-layout: fixed; 
    border-collapse: collapse; 
  }
  .responsive-table th, .responsive-table td {
    padding: 8px;
  }

  @media (max-width: 600px) {
    /* Shrink text and padding */
    .responsive-table th, .responsive-table td {
      font-size: 12px;
      padding: 4px;
    }
    /* Hide unwanted portrait-only columns (by index):
       Conference(2), Undefeated Probability(5),
       Projected Conference Losses(7),
       Schedule Difficulty Rank(8),
       Final 2024 Rank(9)
    */
    .responsive-table th:nth-child(2),
    .responsive-table td:nth-child(2),
    .responsive-table th:nth-child(5),
    .responsive-table td:nth-child(5),
    .responsive-table th:nth-child(7),
    .responsive-table td:nth-child(7),
    .responsive-table th:nth-child(8),
    .responsive-table td:nth-child(8),
    .responsive-table th:nth-child(9),
    .responsive-table td:nth-child(9) {
      display: none;
    }
  }
</style>
""", unsafe_allow_html=True)

# --- Responsive desktop/mobile toggle CSS ---
st.markdown("""
<style>
  .desktop-table { display: block; }
  .mobile-table { display: none; }
  @media (max-width: 600px) {
    .desktop-table { display: none !important; }
    .mobile-table { display: block !important; }
  }
</style>
""", unsafe_allow_html=True)  

# --- Responsive desktop/mobile toggle CSS ---
st.markdown("""
<style>
  .desktop-table { display: block; }
  .mobile-table  { display: none; }
  @media (max-width: 600px) {
    .desktop-table { display: none !important; }
    .mobile-table  { display: block !important; }
  }
</style>
""", unsafe_allow_html=True)

# --- Responsive desktop/mobile toggle CSS ---
st.markdown("""
<style>
  .desktop-table { display: block; }
  .mobile-table { display: none; }
  @media (max-width: 600px) {
    .desktop-table { display: none !important; }
    .mobile-table { display: block !important; }
  }
</style>
""", unsafe_allow_html=True)

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
    # Sidebar filters
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", df.columns.tolist(), df.columns.tolist().index("Preseason Rank")
    )
    asc = st.sidebar.checkbox("Ascending order", True)

    # Prepare DataFrame
    df = df_expected.copy()
    if team_search:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    df = df.sort_values(by="Preseason Rank")
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # Compute bounds for styling
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    # Columns always in desktop table
    cols_rank = df.columns.tolist()
    # --- Desktop table ---
    html = [
    '<div style="max-height:600px;">',
    '<table class="responsive-table">',
    ...
]

    for c in cols_rank:
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            th += " white-space:nowrap; min-width:200px;"
        html.append(f"<th style='{th}'>{c}</th>")
    html.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        html.append("<tr>")
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL", "")
                cell = (
                    f'<img src="{logo}" width="24" />' if logo.startswith("http") else v
                )
            elif c == "OVER/UNDER Pick" and isinstance(v, str):
                cell = v
                if v.upper().startswith("OVER"): td += " background-color:#28a745; color:white;"
                elif v.upper().startswith("UNDER"): td += " background-color:#dc3545; color:white;"
            elif c == "Power Rating" and pd.notnull(v):
                t = (v-pr_min)/(pr_max-pr_min) if pr_max>pr_min else 0
                r,g,b = [int(255+(x-255)*t) for x in (0,32,96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            elif c == "Average Game Quality" and pd.notnull(v):
                t = (v-agq_min)/(agq_max-agq_min) if agq_max>agq_min else 0
                r,g,b = [int(255+(x-255)*t) for x in (0,32,96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                inv = 1-(v-sdr_min)/(sdr_max-sdr_min) if sdr_max>sdr_min else 0
                r,g,b = [int(255+(x-255)*inv) for x in (0,32,96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                cell = v
            html.append(f"<td style='{td}'>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    # --- Mobile simplified table for portrait mode ---
    html_mobile = [
        '<div class="mobile-table" style="width:100%;">',
        '<table style="width:100%; table-layout:fixed; border-collapse:collapse;">',
        '<thead><tr>',
        '<th>Preseason Rank</th>',
        '<th>Team</th>',
        '<th>Vegas Win Total</th>',
        '<th>Projected Overall Wins</th>',
        '<th>Projected Overall Losses</th>',
        '<th>OVER/UNDER Pick</th>',
        '<th>Average Game Quality</th>',
        '<th>Schedule Difficulty Rating</th>',
        '</tr></thead><tbody>'
    ]
    for _, row in df.iterrows():
        pr = row["Preseason Rank"]
        logo = row.get("Logo URL", "")
        team_cell = f'<img src="{logo}" width="24"/>' if logo.startswith("http") else ''
        vegas = row["OVER/UNDER Pick"]
        ow = row["Projected Overall Wins"]
        ol = row["Projected Overall Losses"]
        agq = f"{row['Average Game Quality']:.1f}" if pd.notnull(row['Average Game Quality']) else ''
        sdr = f"{row['Schedule Difficulty Rating']:.1f}" if pd.notnull(row['Schedule Difficulty Rating']) else ''
        html_mobile.append(
            f"<tr>"
            f"<td>{pr}</td><td>{team_cell}</td><td>{vegas}</td>"
            f"<td>{ow}</td><td>{ol}</td><td>{vegas}</td>"
            f"<td>{agq}</td><td>{sdr}</td></tr>"
        )
    html_mobile.append("</tbody></table></div>")
    st.markdown("".join(html_mobile), unsafe_allow_html=True)
    # --- Mobile simplified table for portrait phones ---
    html_mobile = [
        '<div class="mobile-table" style="width:100%;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>',
        '<th>Preseason Rank</th>',
        '<th>Team</th>',
        '<th>Vegas Win Total</th>',
        '<th>Projected Overall Wins</th>',
        '<th>Projected Overall Losses</th>',
        '<th>OVER/UNDER Pick</th>',
        '<th>Average Game Quality</th>',
        '<th>Schedule Difficulty Rating</th>',
        '</tr></thead><tbody>'
    ]
    for _, row in df.iterrows():
        pr = row["Preseason Rank"]
        logo = row.get("Logo URL") or ""
        team_cell = f'<img src="{logo}" width="24"/>' if isinstance(logo, str) and logo.startswith("http") else ""
        vegas = row["OVER/UNDER Pick"]
        ow = row["Projected Overall Wins"]
        ol = row["Projected Overall Losses"]
        agq = f"{row['Average Game Quality']:.1f}"
        sdr = f"{row['Schedule Difficulty Rating']:.1f}"
        html_mobile.append(
            f"<tr>"
            f"<td>{pr}</td><td>{team_cell}</td><td>{vegas}</td>"
            f"<td>{ow}</td><td>{ol}</td><td>{vegas}</td>"
            f"<td>{agq}</td><td>{sdr}</td>"
            f"</tr>"
        )
    html_mobile.append('</tbody></table></div>')
    st.markdown("".join(html_mobile), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")

    # 1) Summary metrics
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

    # 2) Merge and normalize conference logos
    logos_conf = logos_df.copy()
    if "Image URL" in logos_conf.columns:
        logos_conf.rename(columns={"Image URL": "Logo URL"}, inplace=True)
    if "Team" in logos_conf.columns and "Conference" not in logos_conf.columns:
        logos_conf.rename(columns={"Team": "Conference"}, inplace=True)
    # drop hyphens & uppercase for matching
    logos_conf["Conference"] = (
        logos_conf["Conference"]
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
    # apply same normalization to summary
    summary["Conference"] = (
        summary["Conference"]
        .str.strip()
        .str.replace("-", "", regex=False)
        .str.upper()
    )
        # merge in logo URLs
    if {"Conference", "Logo URL"}.issubset(logos_conf.columns):
        summary = summary.merge(
            logos_conf[["Conference", "Logo URL"]],
            on="Conference",
            how="left"
        )
    # 3) Compute bounds
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()

            # 4) Summary table with conference logos
    left, right = st.columns([1,1])
    with left:
        html_sum = [
            '<div style="overflow-x:auto; max-height:600px; overflow-y:auto;">',
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
                    if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                        cell = (
                            f'<div style="display:flex;align-items:center;">'
                            f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                        )
                    else:
                        cell = v
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
    # No scatterplot on the right
    # (scatter removed per request)
    # 5) Detailed conference table
    st.markdown("---")
    sel = st.selectbox("Select conference for details", summary["Conference"].tolist())
    df_conf = df_expected[df_expected["Conference"] == sel].copy()
    df_conf.insert(0, "Projected Conference Finish", range(1, len(df_conf) + 1))
        # (team logos already in df_expected via initial merge)
    cols_conf = [
        "Projected Conference Finish", "Preseason Rank", "Team", "Power Rating",
        "Projected Conference Wins", "Projected Conference Losses",
        "Average Game Quality", "Schedule Difficulty Rank", "Schedule Difficulty Rating"
    ]
    bounds = {
        "Power Rating": (df_conf["Power Rating"].min(), df_conf["Power Rating"].max()),
        "Average Game Quality": (df_conf["Average Game Quality"].min(), df_conf["Average Game Quality"].max()),
        "Schedule Difficulty Rating": (df_conf["Schedule Difficulty Rating"].min(), df_conf["Schedule Difficulty Rating"].max())
    }

    html_conf = ['<div style="max-height:500px; overflow-y:auto;">', '<table style="width:100%; border-collapse:collapse;">', '<thead><tr>']
    for c in cols_conf:
        th = 'border:1px solid #ddd; padding:8px; text-align:center; background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        if c == "Team": th += " white-space:nowrap; min-width:200px;"
        html_conf.append(f"<th style='{th}'>{c}</th>")
    html_conf.append('</tr></thead><tbody>')
    for _, row in df_conf.iterrows():
        html_conf.append('<tr>')
        for c in cols_conf:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and logo.startswith("http"):
                    cell = (
                        f'<div style="display:flex;align-items:center;">'
                        f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                    )
                else:
                    cell = v
            elif c in ["Projected Conference Finish", "Preseason Rank", "Schedule Difficulty Rank"]:
                cell = int(v)
            elif c in ["Projected Conference Wins", "Projected Conference Losses"]:
                cell = f"{v:.1f}"
            else:
                mn, mx = bounds[c]
                t = (v - mn) / (mx - mn) if mx > mn else 0
                if c == "Schedule Difficulty Rating": t = 1 - t
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'white' if t>0.5 else 'black'};"
                cell = f"{v:.1f}"
            html_conf.append(f"<td style='{td}'>{cell}</td>")
        html_conf.append('</tr>')
    html_conf.append('</tbody></table></div>')
    st.markdown(''.join(html_conf), unsafe_allow_html=True)
# --- Mobile simplified table for portrait phones ---
html_mobile = [
    '<div class="mobile-table" style="width:100%;">',
    '<table style="width:100%; border-collapse:collapse;">',
    '<thead><tr>',
    '<th>Preseason Rank</th>',
    '<th>Team</th>',
    '<th>Vegas Win Total</th>',
    '<th>Projected Overall Wins</th>',
    '<th>Projected Overall Losses</th>',
    '<th>OVER/UNDER Pick</th>',
    '<th>Average Game Quality</th>',
    '<th>Schedule Difficulty Rating</th>',
    '</tr></thead><tbody>'
]
for _, row in df.iterrows():
    pr = row["Preseason Rank"]
    logo = row.get("Logo URL") or ""
    team_cell = f'<img src="{logo}" width="24"/>' if logo.startswith("http") else ""
    vegas = row["OVER/UNDER Pick"]
    ow = row["Projected Overall Wins"]
    ol = row["Projected Overall Losses"]
    agq = f"{row['Average Game Quality']:.1f}"
    sdr = f"{row['Schedule Difficulty Rating']:.1f}"
    html_mobile.append(
        f"<tr>"
        f"<td>{pr}</td><td>{team_cell}</td><td>{vegas}</td>"
        f"<td>{ow}</td><td>{ol}</td><td>{vegas}</td>"
        f"<td>{agq}</td><td>{sdr}</td>"
        f"</tr>"
    )
html_mobile.append('</tbody></table></div>')
st.markdown("".join(html_mobile), unsafe_allow_html=True)
