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

# --- Load Data ---
# Path to the workbook
data_path = Path(__file__).parent / "Preseason 2025.xlsm"
# Load expected wins and logos sheets
df_expected = load_sheet(data_path, "Expected Wins", header=1)
logos_df = load_sheet(data_path, "Logos", header=1)

# Normalize logo column
if "Image URL" in logos_df.columns:
    logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)

# Merge logos into expected wins
temp = logos_df[["Team", "Logo URL"]].copy()
df_expected = df_expected.merge(temp, on="Team", how="left")

# --- Streamlit config ---
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🎯 College Football 2025 Pre-Season Preview")

# --- Data cleaning & renaming ---
# Drop empty helper columns
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
# Drop known blanks
df_expected.drop(columns=["Column1", "Column3"], inplace=True, errors='ignore')
# Rename columns
enable_rename = {
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
df_expected.rename(columns=enable_rename, inplace=True)
# Add Preseason Rank
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
# Format probabilities
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = (
        df_expected["Undefeated Probability"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "")
    )
# Round numeric columns (excluding ranks)
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

# --- Sidebar & tab selection ---
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Team Dashboards", "Charts & Graphs"]
)

# --- Rankings Tab ---
if tab == "Rankings":
    st.header("📋 Rankings")
    # Filters
    team_search = st.sidebar.text_input("Search team...", "")
    conf_search = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox("Sort by column", df_expected.columns, index=df_expected.columns.get_loc("Preseason Rank"))
    asc = st.sidebar.checkbox("Ascending order", True)

    df = df_expected.copy()
    # Re-merge logos (ensure present)
    df = df.merge(temp, on="Team", how="left")

    # Apply filters
    if team_search:
        df = df[df["Team"].str.contains(team_search, case=False, na=False)]
    if conf_search and "Conference" in df.columns:
        df = df[df["Conference"].str.contains(conf_search, case=False, na=False)]
    # Sort
    df = df.sort_values(by="Preseason Rank")
    try:
        df = df.sort_values(by=sort_col, ascending=asc)
    except TypeError:
        df = df.sort_values(by=sort_col, ascending=asc, key=lambda s: s.astype(str))

    # Determine columns to display
    all_cols = df.columns.tolist()
    if "Schedule Difficulty Rating" in all_cols:
        end_idx = all_cols.index("Schedule Difficulty Rating")
        cols_rank = all_cols[: end_idx + 1]
    else:
        cols_rank = all_cols.copy()

    # Compute color bounds
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    # Build HTML table\ n    html = ['<div style="max-height:600px; overflow-y:auto;">', '<table style="width:100%; border-collapse:collapse;">', '<thead><tr>']
    for c in cols_rank:
        th_style = ('border:1px solid #ddd; padding:8px; text-align:center; ' 'background-color:#002060; color:white; position:sticky; top:0; z-index:2;')
        if c == "Team": th_style += " white-space:nowrap; min-width:200px;"
        html.append(f"<th style='{th_style}'>{c}</th>")
    html.append('</tr></thead><tbody>')

    for _, row in df.iterrows():
        html.append('<tr>')
        for c in cols_rank:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            # Team with logo
            if c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and logo.startswith("http"):
                    cell = (f'<div style="display:flex;align-items:center;">'
                            f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>')
                else:
                    cell = v
            # OVER/UNDER pick coloring
            elif c == "OVER/UNDER Pick" and isinstance(v, str):
                cell = v
                if v.upper().startswith("OVER"):
                    td_style += " background-color:#28a745; color:white;"
                elif v.upper().startswith("UNDER"):
                    td_style += " background-color:#dc3545; color:white;"
            # Power Rating gradient
            elif c == "Power Rating" and pd.notnull(v):
                t = (v - pr_min) / (pr_max - pr_min) if pr_max>pr_min else 0
                r,g,b = [int(255+(x-255)*t) for x in (0,32,96)]
                td_style += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            # Average Game Quality gradient
            elif c == "Average Game Quality" and pd.notnull(v):
                t = (v-agq_min)/(agq_max-agq_min) if agq_max>agq_min else 0
                r,g,b = [int(255+(x-255)*t) for x in (0,32,96)]
                td_style += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            # Schedule Difficulty Rating inverse gradient
            elif c == "Schedule Difficulty Rating" and pd.notnull(v):
                inv = 1 - ((v-sdr_min)/(sdr_max-sdr_min) if sdr_max>sdr_min else 0)
                r,g,b = [int(255+(x-255)*inv) for x in (0,32,96)]
                td_style += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                cell = v
            html.append(f"<td style='{td_style}'>{cell}</td>")
        html.append('</tr>')
    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

# --- Conference Overviews Tab ---
elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")

    # 1) Summary metrics
    summary = df_expected.groupby("Conference").agg(
        **{
            "# Teams": ("Preseason Rank","count"),
            "Avg. Power Rating": ("Power Rating","mean"),
            "Avg. Game Quality": ("Average Game Quality","mean"),
            "Avg. Schedule Difficulty": ("Schedule Difficulty Rating","mean"),
        }
    ).reset_index()
    summary[["Avg. Power Rating","Avg. Game Quality","Avg. Schedule Difficulty"]] = summary[["Avg. Power Rating","Avg. Game Quality","Avg. Schedule Difficulty"]].round(1)

    # 2) Merge conference logos
    logos_conf = logos_df.copy()
    if "Image URL" in logos_conf.columns:
        logos_conf.rename(columns={"Image URL":"Logo URL"}, inplace=True)
    if "Team" in logos_conf.columns and "Conference" not in logos_conf.columns:
        logos_conf.rename(columns={"Team":"Conference"}, inplace=True)
    logos_conf["Conference"] = logos_conf["Conference"].str.strip()
    summary["Conference"] = summary["Conference"].str.strip()
    summary = summary.merge(
        logos_conf[["Conference","Logo URL"]], on="Conference", how="left"
    )

    # 3) Compute bounds
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()

    # 4) Layout: summary and scatter
    left, right = st.columns(2)
    with left:
        html = ['<div style="overflow-x:auto; max-height:600px; overflow-y:auto;">', '<table style="width:100%; border-collapse:collapse;">', '<thead><tr>']
        cols = ["Conference","# Teams","Avg. Power Rating","Avg. Game Quality","Avg. Schedule Difficulty"]
        for c in cols:
            th_style = 'border:1px solid #ddd; padding:8px; text-align:center; background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
            if c=="Conference": th_style += " white-space:nowrap; min-width:150px;"
            html.append(f"<th style='{th_style}'>{c}</th>")
        html.append('</tr></thead><tbody>')
        for _,row in summary.iterrows():
            html.append('<tr>')
            for c in cols:
                v = row[c]
                td_style='border:1px solid #ddd; padding:8px; text-align:center;'
                if c=="Conference":
                    logo=row.get("Logo URL")
                    if pd.notnull(logo) and logo.startswith("http"):
                        cell=(f'<div style="display:flex;align-items:center;">'
                              f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>')
                    else:
                        cell=v
                elif c=="# Teams":
                    cell=int(v)
                elif c in ["Avg. Power Rating","Avg. Game Quality"]:
                    mn,mx=(pr_min,pr_max) if c=="Avg. Power Rating" else (agq_min,agq_max)
                    t=(v-mn)/(mx-mn) if mx>mn else 0
                    r,g,b=[int(255+(x-255)*t) for x in (0,32,96)]
                    td_style+=f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                    cell=f"{v:.1f}"
                else:
                    inv=1-((v-sdr_min)/(sdr_max-sdr_min) if sdr_max>sdr_min else 0)
                    r,g,b=[int(255+(x-255)*inv) for x in (0,32,96)]
                    td_style+=f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                    cell=f"{v:.1f}"
                html.append(f"<td style='{td_style}'>{cell}</td>")
            html.append('</tr>')
        html.append('</tbody></table></div>')
        st.markdown(''.join(html), unsafe_allow_html=True)
    with right:
        chart_df = df_expected.copy()
        chart_df = chart_df.merge(temp, on="Team", how="left")
        # scatter with logos
        scatter = (alt.Chart(chart_df)
                   .mark_image(width=24, height=24)
                   .encode(
                       x="Average Game Quality:Q",
                       y="Power Rating:Q",
                       url="Logo URL:N",
                       tooltip=["Team","Power Rating","Average Game Quality"]
                   )
                   .properties(height=600))
        st.altair_chart(scatter.interactive(), use_container_width=True)

    st.markdown("---")
    sel = st.selectbox("Select conference for details", summary["Conference"].tolist())
    df_conf = df_expected[df_expected["Conference"]==sel].copy()
    df_conf.insert(0,"Projected Conference Finish", range(1, len(df_conf)+1))
    # merge logos for detail table
    df_conf = df_conf.merge(temp, on="Team", how="left")

    # build detail HTML\ n    cols_d = ["Projected Conference Finish","Preseason Rank","Team","Power Rating",
              "Projected Conference Wins","Projected Conference Losses",
              "Average Game Quality","Schedule Difficulty Rank","Schedule Difficulty Rating"]
    bounds = {c: (df_conf[c].min(), df_conf[c].max()) for c in ["Power Rating","Average Game Quality","Schedule Difficulty Rating"]}
    html_conf = ['<div style="max-height:500px; overflow-y:auto;">', '<table style="width:100%; border-collapse:collapse;">', '<thead><tr>']
    for c in cols_d:
        th_style = 'border:1px solid #ddd; padding:8px; text-align:center; background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        if c=="Team": th_style += " white-space:nowrap; min-width:200px;"
        html_conf.append(f"<th style='{th_style}'>{c}</th>")
    html_conf.append('</tr></thead><tbody>')

    for _, row in df_conf.iterrows():
        html_conf.append('<tr>')
        for c in cols_d:
            v = row[c]
            td_style='border:1px solid #ddd; padding:8px; text-align:center;'
            if c=="Team":
                logo=row.get("Logo URL")
                if pd.notnull(logo) and logo.startswith("http"):
                    cell=(f'<div style="display:flex;align-items:center;">'
                          f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>')
                else:
                    cell=v
            elif c in ["Projected Conference Finish","Preseason Rank","Schedule Difficulty Rank"]:
                cell=int(v)
            elif c in ["Projected Conference Wins","Projected Conference Losses"]:
                cell=f"{v:.1f}"
            else:
                mn,mx=bounds[c]
                t=(v-mn)/(mx-mn) if mx>mn else 0
                if c=="Schedule Difficulty Rating": t=1-t
                r,g,b=[int(255+(x-255)*t) for x in (0,32,96)]
                td_style+=f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'white' if t>0.5 else 'black'};"
                cell=f"{v:.1f}"
            html_conf.append(f"<td style='{td_style}'>{cell}</td>")
        html_conf.append('</tr>')
    html_conf.append('</tbody></table></div>')
    st.markdown(''.join(html_conf), unsafe_allow_html=True)

# -- Team Dashboards & Charts omitted for brevity --
