import xlwings as xw
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

# Load workbook and 'Expected Wins' sheet
DATA_FILE = Path(__file__).parent / "Preseason 2025.xlsm"
wb = xw.Book(DATA_FILE)
expected = wb.sheets["Expected Wins"]
df_expected = expected.range("C2").options(
    pd.DataFrame, header=1, index=False, expand="table"
).value

# Clean and rename expected wins
# Drop blank and placeholder columns
df_expected.drop(
    columns=[c for c in df_expected.columns if str(c).strip() == ""],
    inplace=True, errors='ignore'
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
# Preseason Rank
df_expected.insert(0, "Preseason Rank", range(1, len(df_expected) + 1))
# Format Undefeated Probability as percentage
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = df_expected["Undefeated Probability"].apply(
        lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
    )
# Round numeric columns except rank ones
num_cols = df_expected.select_dtypes(include=["number"]).columns.tolist()
num_cols = [c for c in num_cols if c not in ["Preseason Rank", "Schedule Difficulty Rank"]]
if num_cols:
    df_expected[num_cols] = df_expected[num_cols].round(1)
# SDR as int
if "Schedule Difficulty Rating" in df_expected.columns:
    df_expected["Schedule Difficulty Rating"] = df_expected["Schedule Difficulty Rating"].round(1)

# Sidebar navigation
tab = st.sidebar.radio(
    "Navigation", ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

if tab == "Rankings":
    st.header("📋 Rankings")
    # Sidebar filters
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", df_expected.columns.tolist(), index=0
    )
    asc = st.sidebar.checkbox("Ascending order", value=True)
    # Prepare DataFrame
    df = df_expected.copy()
    if team_search and "Team" in df.columns:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=asc)
    display_df = df.copy()

    # Color scale endpoints
    pr_min = display_df["Power Rating"].min() if "Power Rating" in display_df.columns else 0
    pr_max = display_df["Power Rating"].max() if "Power Rating" in display_df.columns else 1
    agq_min = display_df["Average Game Quality"].min() if "Average Game Quality" in display_df.columns else 0
    agq_max = display_df["Average Game Quality"].max() if "Average Game Quality" in display_df.columns else 1
    sdr_min = display_df["Schedule Difficulty Rating"].min() if "Schedule Difficulty Rating" in display_df.columns else 0
    sdr_max = display_df["Schedule Difficulty Rating"].max() if "Schedule Difficulty Rating" in display_df.columns else 1

    # Load logos and embed
    try:
        df_images = wb.sheets["Logos"].range("A1").options(
            pd.DataFrame, header=1, index=False, expand="table"
        ).value
    except Exception:
        df_images = pd.DataFrame()
    if not df_images.empty and {"Team","Image URL"}.issubset(df_images.columns):
        display_df = display_df.merge(df_images, on="Team", how="left")
    if "Image URL" in display_df.columns:
        display_df["Team"] = display_df.apply(
            lambda r: (
                f'<img src="{r["Image URL"]}" width="24" style="vertical-align:middle; margin-right:8px;">{r["Team"]}'
                if pd.notnull(r["Image URL"]) else r["Team"]
            ), axis=1
        )
        display_df.drop(columns="Image URL", inplace=True, errors='ignore')

    # Render scrollable, frozen-header table
    cols = display_df.columns.tolist()
    html = [
        '<div style="max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">'
    ]
    # Header with sticky cells
    html.append('<thead><tr>')
    for c in cols:
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; '
            'position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            th_style += ' white-space:nowrap; min-width:200px;'
        html.append(f'<th style="{th_style}">{c}</th>')
    html.append('</tr></thead><tbody>')
    # Data rows
    for _, r in display_df.iterrows():
        html.append('<tr>')
        for c in cols:
            v = r[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            # Power Rating
            if c == "Power Rating" and pd.notnull(v):
                t = (v - pr_min)/(pr_max - pr_min) if pr_max>pr_min else 0
                rch = int(255 + (0-255)*t)
                gch = int(255 + (32-255)*t)
                bch = int(255 + (96-255)*t)
                color = f"#{rch:02x}{gch:02x}{bch:02x}"
                txt = "black" if t<0.5 else "white"
                td_style += f" background-color:{color}; color:{txt};"
                cell = f"{v:.1f}"
            # Average Game Quality
            elif c == "Average Game Quality" and pd.notnull(v):
                t2 = (v - agq_min)/(agq_max-agq_min) if agq_max>agq_min else 0
                r2 = int(255 + (0-255)*t2)
                g2 = int(255 + (32-255)*t2)
                b2 = int(255 + (96-255)*t2)
                clr2 = f"#{r2:02x}{g2:02x}{b2:02x}"
                txt2 = "black" if t2<0.5 else "white"
                td_style += f" background-color:{clr2}; color:{txt2};"
                cell = f"{v:.1f}"
            # Schedule Difficulty Rating inverse
            elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                t3 = (v - sdr_min)/(sdr_max-sdr_min) if sdr_max>sdr_min else 0
                inv = 1 - t3
                ri = int(255 + (0-255)*inv)
                gi = int(255 + (32-255)*inv)
                bi = int(255 + (96-255)*inv)
                clr3 = f"#{ri:02x}{gi:02x}{bi:02x}"
                txt3 = "black" if inv<0.5 else "white"
                td_style += f" background-color:{clr3}; color:{txt3};"
                cell = f"{v:.1f}"
            # OVER/UNDER Pick
            elif c == "OVER/UNDER Pick":
                pick = str(v).upper()
                if pick == "OVER": td_style += " background-color:#008000; color:white;"
                if pick == "UNDER": td_style += " background-color:#FF0000; color:white;"
                cell = pick
            else:
                cell = v
            if c == "Team": td_style += " white-space:nowrap;"
            html.append(f'<td style="{td_style}">{cell}</td>')
        html.append('</tr>')
    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    st.info("Coming soon: Conference overview analysis will appear here.")=

elif tab == "Team Dashboards":
    st.header("📊 Team Dashboards")
    team = st.sidebar.selectbox("Choose a team", df_expected["Team"].tolist())
    dash = wb.sheets["Dashboard"]
    dash.range("B1").value = team
    st.subheader(f"Dashboard for {team}")
    st.table(dash.range("A1:Z50").value)

elif tab == "Charts & Graphs":
    st.header("📈 Charts & Graphs")
    cg = wb.sheets["Charts and Graphs"]
    c1, c2 = st.columns(2)
    with c1:
        for i, ch in enumerate(cg.charts[:2], start=1):
            fn = f"chart_{i}.png"; ch.api.Export(str(fn)); st.image(fn, caption=ch.name)
    with c2:
        for i, ch in enumerate(cg.charts[2:], start=3):
            fn = f"chart_{i}.png"; ch.api.Export(str(fn)); st.image(fn, caption=ch.name)

