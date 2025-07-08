import pandas as pd
import streamlit as st
from pathlib import Path

def load_expected(data_path: Path) -> pd.DataFrame:
    try:
        import xlwings as xw
        wb  = xw.Book(data_path)
        sht = wb.sheets["Expected Wins"]
        df  = (sht.range("C2")
                  .options(pd.DataFrame, header=1, index=False, expand="table")
                  .value)
    except ImportError:
        df = pd.read_excel(
            data_path,
            sheet_name="Expected Wins",
            engine="openpyxl",
            header=1
        )
    return df

def load_logos(data_path: Path) -> pd.DataFrame:
    try:
        import xlwings as xw
        wb  = xw.Book(data_path)
        sht = wb.sheets["Logos"]
        df  = (sht.range("A1")
                  .options(pd.DataFrame, header=1, index=False, expand="table")
                  .value)
    except ImportError:
        df = pd.read_excel(
            data_path,
            sheet_name="Logos",
            engine="openpyxl",
            header=1
        )
    return df

# ─── right here, only loader calls ──────────────────────────────────────────
DATA_FILE   = Path(__file__).parent / "Preseason 2025.xlsm"
df_expected = load_expected(DATA_FILE)
logos_df    = load_logos(DATA_FILE)
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
)
st.title("🎯 College Football 2025 Pre-Season Preview")

# …now reference ONLY df_expected (not `expected.range`) in all of the cleaning,
# filtering, table-building and chart code below…


# …the rest of your cleaning, sidebar, tabs, etc., all using df_expected…


# Load workbook and data
DATA_FILE = Path(__file__).parent / "Preseason 2025.xlsm"
df_expected = expected.range("C2").options(
    pd.DataFrame, header=1, index=False, expand="table"
).value

# Clean and rename columns
df_expected.drop(columns=[c for c in df_expected.columns if str(c).strip()==""], inplace=True, errors='ignore')
for col in ["Column1", "Column3"]:
    df_expected.drop(columns=col, inplace=True, errors='ignore')
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

# Add Preseason Rank and format probabilities
df_expected.insert(0, "Preseason Rank", range(1, len(df_expected) + 1))
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = df_expected["Undefeated Probability"].apply(
        lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
    )

# Round numeric columns except ranks
numeric_cols = df_expected.select_dtypes(include=["number"]).columns.tolist()
numeric_cols = [c for c in numeric_cols if c not in ["Preseason Rank", "Schedule Difficulty Rank"]]
if numeric_cols:
    df_expected[numeric_cols] = df_expected[numeric_cols].round(1)
if "Schedule Difficulty Rating" in df_expected.columns:
    df_expected["Schedule Difficulty Rating"] = df_expected["Schedule Difficulty Rating"].round(1)

# Sidebar navigation
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
    sort_col = st.sidebar.selectbox("Sort by column", df_expected.columns.tolist(), index=0)
    asc = st.sidebar.checkbox("Ascending order", True)

    # Filter and sort data
    df = df_expected.copy()
    if team_search and "Team" in df.columns:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=asc)

    # Compute color bounds
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    # Load team logos
    try:
        if "Team" in logos.columns and "Image URL" in logos.columns:
            logos.rename(columns={"Image URL": "Logo URL"}, inplace=True)
            df = df.merge(logos[["Team", "Logo URL"]], on="Team", how="left")
    except Exception:
        pass

    # Build HTML table
    html_rank = [
        '<div style="max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>'
    ]
    cols_rank = [c for c in df.columns if c != "Logo URL"]
    for c in cols_rank:
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        ) + (" white-space:nowrap; min-width:200px;" if c == "Team" else "")
        html_rank.append(f"<th style='{th}'>{c}</th>")
    html_rank.append('</tr></thead><tbody>')

    for _, row in df.iterrows():
        html_rank.append('<tr>')
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL")
                cell = (
                    f'<img src="{logo}" width="24" style="vertical-align:middle; margin-right:8px;">{v}'
                    if pd.notnull(logo) and str(logo).startswith("http") else v
                )
            elif c == "OVER/UNDER Pick":
                if isinstance(v, str) and v.upper().startswith("OVER"):
                    td += " background-color:#28a745; color:white;"
                elif isinstance(v, str) and v.upper().startswith("UNDER"):
                    td += " background-color:#dc3545; color:white;"
                cell = v
            elif c == "Power Rating":
                t = (v - pr_min) / (pr_max - pr_min) if pr_max > pr_min else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            elif c == "Average Game Quality":
                t2 = (v - agq_min) / (agq_max - agq_min) if agq_max > agq_min else 0
                r2, g2, b2 = [int(255 + (x - 255) * t2) for x in (0, 32, 96)]
                td += f" background-color:#{r2:02x}{g2:02x}{b2:02x}; color:{'black' if t2<0.5 else 'white'};"
                cell = f"{v:.1f}"
            elif c == "Schedule Difficulty Rating":
                t3 = (v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 0
                inv = 1 - t3
                ri, gi, bi = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                td += f" background-color:#{ri:02x}{gi:02x}{bi:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                cell = v
            html_rank.append(f"<td style='{td}'>{cell}</td>")
        html_rank.append('</tr>')
    html_rank.append('</tbody></table></div>')
    st.markdown(''.join(html_rank), unsafe_allow_html=True)

# ------ Conference Overviews ------
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")

    # Summary metrics with schedule difficulty
    summary = (
        df_expected.groupby("Conference").agg(
            **{
                "# Teams": ("Preseason Rank", "count"),
                "Avg. Power Rating": ("Power Rating", "mean"),
                "Avg. Game Quality": ("Average Game Quality", "mean"),
                "Avg. Schedule Difficulty": ("Schedule Difficulty Rating", "mean"),
            }
        )
        .reset_index()
    )
    summary[["Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]] = (
        summary[["Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]].round(1)
    )

    # Merge conference logos
    try:
        if "Conference" not in logos_df.columns and "Team" in logos_df.columns:
            logos_df.rename(columns={"Team": "Conference"}, inplace=True)
        if {"Conference", "Image URL"}.issubset(logos_df.columns):
            logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
            summary = summary.merge(
                logos_df[["Conference", "Logo URL"]], on="Conference", how="left"
            )
    except Exception:
        pass

    # Compute gradient bounds and build HTML table
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()

    html_conv = [
        '<div style="overflow-x:auto; max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse; margin-bottom:2rem;">',
        '<thead><tr>'
    ]
    conv_cols = ["Conference", "# Teams", "Avg. Power Rating", "Avg. Game Quality", "Avg. Schedule Difficulty"]
    for c in conv_cols:
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Conference": th_style += ' white-space:nowrap; min-width:150px;'
        html_conv.append(f"<th style='{th_style}'>{c}</th>")
    html_conv.append('</tr></thead><tbody>')

    for _, row in summary.iterrows():
        html_conv.append('<tr>')
        for c in conv_cols:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Conference":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and str(logo).startswith("http"):
                    cell = f'<img src="{logo}" width="24" style="vertical-align:middle; margin-right:8px;">{v}'
                else:
                    cell = v
            elif c == "# Teams":
                cell = int(v)
            elif c == "Avg. Power Rating":
                t = (v - pr_min) / (pr_max - pr_min) if pr_max > pr_min else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td_style += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            elif c == "Avg. Game Quality":
                t2 = (v - agq_min) / (agq_max - agq_min) if agq_max > agq_min else 0
                r2, g2, b2 = [int(255 + (x - 255) * t2) for x in (0, 32, 96)]
                td_style += f" background-color:#{r2:02x}{g2:02x}{b2:02x}; color:{'black' if t2<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                inv = 1 - (v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 1
                ri, gi, bi = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                td_style += f" background-color:#{ri:02x}{gi:02x}{bi:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            html_conv.append(f"<td style='{td_style}'>{cell}</td>")
        html_conv.append('</tr>')
    html_conv.append('</tbody></table></div>')

    # Display summary table and scatterplot
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(''.join(html_conv), unsafe_allow_html=True)
    with col2:
        st.altair_chart(
    alt.Chart(summary)
       .mark_circle(size=60, opacity=0.7)
       .encode(
           x=alt.X("Avg. Game Quality", type="quantitative"),
           y=alt.Y("Avg. Power Rating", type="quantitative"),
           tooltip=[alt.Tooltip("Conference", type="nominal")]
       )
       .interactive(),
    use_container_width=True
)

    # Conference-specific “Projected Conference Wins” table
    st.markdown("---")
    sel_conf = st.selectbox(
        "Select conference for details",
        options=summary["Conference"].tolist(),
        index=0,
    )
    df_conf = df_expected[df_expected["Conference"] == sel_conf].copy()
    try:
        logos = wb.sheets["Logos"].range("A1").options(pd.DataFrame, header=1, index=False, expand="table").value
        if "Team" in logos.columns and "Image URL" in logos.columns:
            logos.rename(columns={"Image URL": "Logo URL"}, inplace=True)
            df_conf = df_conf.merge(logos[["Team", "Logo URL"]], on="Team", how="left")
    except Exception:
        pass
    df_conf = df_conf.sort_values("Projected Conference Wins", ascending=False)
    df_conf.insert(0, "Projected Conference Finish", range(1, len(df_conf) + 1))

    html_conf = [
        '<div style="max-height:500px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>'
    ]
    cols_conf = [
        "Projected Conference Finish",
        "Preseason Rank",
        "Team",
        "Power Rating",
        "Projected Conference Wins",
        "Projected Conference Losses",
        "Average Game Quality",
        "Schedule Difficulty Rank",
        "Schedule Difficulty Rating",
    ]
    pw_min, pw_max = df_conf["Projected Conference Wins"].min(), df_conf["Projected Conference Wins"].max()
    qr_min, qr_max = df_conf["Projected Conference Losses"].min(), df_conf["Projected Conference Losses"].max()
    pr_min_c, pr_max_c = df_conf["Power Rating"].min(), df_conf["Power Rating"].max()
    agq_min_c, agq_max_c = df_conf["Average Game Quality"].min(), df_conf["Average Game Quality"].max()
    sdr_min_c, sdr_max_c = df_conf["Schedule Difficulty Rating"].min(), df_conf["Schedule Difficulty Rating"].max()
    for c in cols_conf:
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        ) + (" white-space:nowrap; min-width:200px;" if c == "Team" else "")
        html_conf.append(f"<th style='{th}'>{c}</th>")
    html_conf.append('</tr></thead><tbody>')
    for _, row in df_conf.iterrows():
        html_conf.append('<tr>')
        for c in cols_conf:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL")
                cell = (
                    f'<img src="{logo}" width="24" style="vertical-align:middle; margin-right:8px;">{v}' if pd.notnull(logo) and str(logo).startswith("http") else v
                )
            elif c in ["Projected Conference Finish", "Preseason Rank"]:
                cell = int(v)
            elif c in ["Projected Conference Wins", "Projected Conference Losses"]:
                cell = f"{v:.1f}"
            elif c == "Power Rating":
                t = (v - pr_min_c) / (pr_max_c - pr_min_c) if pr_max_c > pr_min_c else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'white' if t>0.5 else 'black'};"
                cell = f"{v:.1f}"
            elif c == "Average Game Quality":
                t2 = (v - agq_min_c) / (agq_max_c - agq_min_c) if agq_max_c > agq_min_c else 0
                r2, g2, b2 = [int(255 + (x - 255) * t2) for x in (0, 32, 96)]
                td += f" background-color:#{r2:02x}{g2:02x}{b2:02x}; color:{'white' if t2>0.5 else 'black'};"
                cell = f"{v:.1f}"
            elif c == "Schedule Difficulty Rank":
                cell = int(v)
            else:
                inv = 1 - (v - sdr_min_c) / (sdr_max_c - sdr_min_c) if sdr_max_c > sdr_min_c else 1
                ri, gi, bi = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                td += f" background-color:#{ri:02x}{gi:02x}{bi:02x}; color:{'white' if inv>0.5 else 'black'};"
                cell = f"{v:.1f}"
            html_conf.append(f"<td style='{td}'>{cell}</td>")
        html_conf.append('</tr>')
    html_conf.append('</tbody></table></div>')
    st.markdown(''.join(html_conf), unsafe_allow_html=True)

# ------ Team Dashboards ------
elif tab == "Team Dashboards":
    st.header("📊 Team Dashboards")
    # [Team Dashboards code unchanged]

# ------ Charts & Graphs ------
elif tab == "Charts & Graphs":
    st.header("📈 Charts & Graphs")
    # [Charts & Graphs code unchanged]
