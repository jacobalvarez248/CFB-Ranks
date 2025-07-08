import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt

# Helper to load Excel sheets via xlwings locally, or pandas/openpyxl on Cloud
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

# Load data once at the top
data_path = Path(__file__).parent / "Preseason 2025.xlsm"
df_expected = load_sheet(data_path, "Expected Wins", header=1)
logos_df = load_sheet(data_path, "Logos", header=1)

# Streamlit app configuration and title
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🎯 College Football 2025 Pre-Season Preview")

# --- Data cleaning and renaming ---
# Drop empty helper columns
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
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
    # If present:
    "Final 2024 Rank": "Final 2024 Rank"
}
df_expected.rename(columns=rename_map, inplace=True)
# Add Preseason Rank if not exists, then format probabilities
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = df_expected["Undefeated Probability"].apply(
        lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
    )
# Round numeric columns except ranks
drop_ranks = ["Preseason Rank", "Schedule Difficulty Rank", "Final 2024 Rank"]
numeric_cols = df_expected.select_dtypes(include=["number"]).columns.tolist()
numeric_cols = [c for c in numeric_cols if c not in drop_ranks]
if numeric_cols:
    df_expected[numeric_cols] = df_expected[numeric_cols].round(1)
# Ensure key numeric columns are numeric types
types_to_int = []
for col in ["Preseason Rank", "Final 2024 Rank"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').fillna(0).astype(int)
for col in ["Power Rating", "Average Game Quality", "Schedule Difficulty Rating"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce')
        df_expected[col] = df_expected[col].round(1)

# Sidebar navigation
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# ------ Rankings ------
if tab == "Rankings":
    st.header("📋 Rankings")
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox("Sort by column", df_expected.columns.tolist(), index=df_expected.columns.tolist().index("Preseason Rank"))
    asc = st.sidebar.checkbox("Ascending order", True)
    df = df_expected.copy()
    # Default sort by Preseason Rank
    df = df.sort_values(by="Preseason Rank", ascending=True)
    # Apply filters
    if team_search and "Team" in df.columns:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    # Apply custom sort
    if sort_col in df.columns:
        try:
            df = df.sort_values(by=sort_col, ascending=asc)
        except TypeError:
            df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))
    # Compute color bounds
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()
    # Merge logos
    if {"Team", "Image URL"}.issubset(logos_df.columns):
        logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
        df = df.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")
    # Build HTML table
    html_rank = [
        '<div style="max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>'
    ]
    # Select columns up to Schedule Difficulty Rating
    all_cols = df.columns.tolist()
    if "Schedule Difficulty Rating" in all_cols:
        end_idx = all_cols.index("Schedule Difficulty Rating")
        cols_rank = all_cols[:end_idx+1]
    else:
        cols_rank = df.columns.tolist()
    for c in cols_rank:
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        ) + (" white-space:nowrap; min-width:200px;" if c == "Team" else "")
        html_rank.append(f"<th style='{th_style}'>{c}</th>")
    html_rank.append('</tr></thead><tbody>')
    for _, row in df.iterrows():
        html_rank.append('<tr>')
        for c in cols_rank:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c in ["Preseason Rank", "Final 2024 Rank"]:
                cell = int(v)
            elif c == "Team":
                logo = row.get("Logo URL")
                cell = (
                    f'<img src="{logo}" width="24" style="vertical-align:middle; margin-right:8px;">{v}' if pd.notnull(logo) and str(logo).startswith("http") else v
                )
            elif c == "OVER/UNDER Pick":
                cell = v
                if isinstance(v, str):
                    if v.upper().startswith("OVER"):
                        td_style += " background-color:#28a745; color:white;"
                    elif v.upper().startswith("UNDER"):
                        td_style += " background-color:#dc3545; color:white;"
            elif c == "Power Rating":
                t = (v - pr_min) / (pr_max - pr_min) if pr_max > pr_min else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td_style += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}" if pd.notnull(v) else ""
            elif c == "Average Game Quality":
                t2 = (v - agq_min) / (agq_max - agq_min) if agq_max > agq_min else 0
                r2, g2, b2 = [int(255 + (x - 255) * t2) for x in (0, 32, 96)]
                td_style += f" background-color:#{r2:02x}{g2:02x}{b2:02x}; color:{'black' if t2<0.5 else 'white'};"
                cell = f"{v:.1f}" if pd.notnull(v) else ""
            elif c == "Schedule Difficulty Rating":
                t3 = (v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 0
                inv = 1 - t3
                ri, gi, bi = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                td_style += f" background-color:#{ri:02x}{gi:02x}{bi:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}" if pd.notnull(v) else ""
            else:
                cell = v
            html_rank.append(f"<td style='{td_style}'>{cell}</td>")
        html_rank.append('</tr>')
    html_rank.append('</tbody></table></div>')
    st.markdown(''.join(html_rank), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # (existing implementation above)

# ------ Team Dashboards ------
elif tab == "Team Dashboards":
    st.header("📊 Team Dashboards")
    # Let user select team
    team = st.sidebar.selectbox(
        "Select Team",
        options=df_expected["Team"].tolist()
    )
    df_team = df_expected[df_expected["Team"] == team].copy()
    # Display team summary
    st.subheader(f"Preseason Data for {team}")
    st.table(df_team)

# ------ Charts & Graphs ------
elif tab == "Charts & Graphs":
    st.header("📈 Charts & Graphs")
    # Power Rating distribution
    chart_df = df_expected[["Team","Power Rating"]].dropna()
    bar = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X('Power Rating:Q', bin=True),
        y='count()',
        tooltip=['count()']
    ).properties(title="Power Rating Distribution")
    st.altair_chart(bar, use_container_width=True)
    # Scatter: Power vs Game Quality
    scatter = alt.Chart(df_expected).mark_circle(size=60, opacity=0.7).encode(
        x=alt.X("Average Game Quality", type="quantitative"),
        y=alt.Y("Power Rating", type="quantitative"),
        color="Conference:N",
        tooltip=["Team","Power Rating","Average Game Quality"]
    ).interactive().properties(title="Power Rating vs Game Quality")
    st.altair_chart(scatter, use_container_width=True)
