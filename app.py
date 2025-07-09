
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

# --- Desktop/Mobile Toggle CSS ---
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

st.markdown("""
<style>
  .responsive-table { overflow-x: hidden; width: 100%; -webkit-overflow-scrolling: touch; }
  .responsive-table table { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .responsive-table th, .responsive-table td { padding: 8px; }
  .mobile-table { width: 100%; overflow-x: hidden; }
  .mobile-table table { width: 100%; table-layout: fixed; border-collapse: collapse; }
  @media (max-width: 600px) {
    .responsive-table th, .responsive-table td,
    .mobile-table th, .mobile-table td { font-size: 12px; padding: 4px; }
    /* Hide unwanted portrait-only columns by index */
    .responsive-table th:nth-child(2), .responsive-table td:nth-child(2),
    .responsive-table th:nth-child(5), .responsive-table td:nth-child(5),
    .responsive-table th:nth-child(7), .responsive-table td:nth-child(7),
    .responsive-table th:nth-child(8), .responsive-table td:nth-child(8),
    .responsive-table th:nth-child(9), .responsive-table td:nth-child(9) {
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

    # ---- Filters ----
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox("Sort by column", df_expected.columns.tolist(),
                                    df_expected.columns.tolist().index("Preseason Rank"))
    asc = st.sidebar.checkbox("Ascending order", True)

    # ---- Prepare DataFrame ----
    df = df_expected.copy()
    if team_search:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    df = df.sort_values("Preseason Rank", ascending=True)
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # ---- Compute bounds for styling ----
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    # ---- Desktop Table ----
    html_desktop = [
        '<div class="desktop-table" style="max-height:600px; overflow-y:auto;">',
        '<table class="responsive-table" style="border-collapse:collapse; width:100%;">',
        '<thead><tr>'
    ]
    cols = ["Preseason Rank","Team","Vegas Win Total","Projected Overall Wins",
            "Projected Overall Losses","OVER/UNDER Pick","Average Game Quality",
            "Schedule Difficulty Rating"]
    for c in cols:
        th = ('border:1px solid #ddd; padding:8px; text-align:center; '
              'background-color:#002060; color:white; position:sticky; top:0;')
        if c == "Team":
            th += " white-space:nowrap; min-width:150px;"
        html_desktop.append(f"<th style='{th}'>{c}</th>")
    html_desktop.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        html_desktop.append("<tr>")
        for c in cols:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            # Team with logo
            if c == "Team":
                logo = row.get("Logo URL","")
                cell = f'<img src="{logo}" width="24" />' if isinstance(logo,str) and logo.startswith("http") else ""
            # OVER/UNDER Pick
            elif c == "OVER/UNDER Pick":
                cell = v
                if isinstance(v,str) and v.upper().startswith("OVER"):
                    td += " background-color:#28a745; color:white;"
                elif isinstance(v,str) and v.upper().startswith("UNDER"):
                    td += " background-color:#dc3545; color:white;"
            # Power Rating (not shown here but you can reinsert)
            # Average Game Quality
            elif c == "Average Game Quality" and pd.notnull(v):
                t = (v - agq_min) / (agq_max - agq_min) if agq_max>agq_min else 0
                r,g,b = [int(255+(x-255)*t) for x in (0,32,96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            # Schedule Difficulty Rating
            elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                inv = 1 - ((v - sdr_min)/(sdr_max - sdr_min) if sdr_max>sdr_min else 0)
                r,g,b = [int(255+(x-255)*inv) for x in (0,32,96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                cell = v if not pd.isna(v) else ""
            html_desktop.append(f"<td style='{td}'>{cell}</td>")
        html_desktop.append("</tr>")
    html_desktop.append("</tbody></table></div>")
    st.markdown("".join(html_desktop), unsafe_allow_html=True)

    # ---- Mobile Table ----
    html_mobile = [
        '<div class="mobile-table" style="width:100%;">',
        '<table class="responsive-table" style="border-collapse:collapse; width:100%;">',
        '<thead><tr>'
    ]
    for c in cols:
        html_mobile.append(f"<th style='padding:4px; text-align:center; font-size:12px;'>{c}</th>")
    html_mobile.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        pr = row["Preseason Rank"]
        logo = row.get("Logo URL","")
        team_cell = f'<img src=\"{logo}\" width=\"24\"/>' if isinstance(logo,str) and logo.startswith("http") else ""
        vegas = row["OVER/UNDER Pick"]
        ow = row["Projected Overall Wins"]
        ol = row["Projected Overall Losses"]
        agq = row["Average Game Quality"]
        sdr = row["Schedule Difficulty Rating"]
        # style mobile cells similarly
        html_mobile.append(
            f"<tr>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{pr}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{team_cell}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{vegas}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{ow}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{ol}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{vegas}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{(f\"{agq:.1f}\" if pd.notnull(agq) else \"\")}</td>"
            f"<td style='padding:4px; font-size:12px;text-align:center;'>{(f\"{sdr:.1f}\" if pd.notnull(sdr) else \"\")}</td>"
            f"</tr>"
        )
    html_mobile.append("</tbody></table></div>")
    st.markdown("".join(html_mobile), unsafe_allow_html=True)

