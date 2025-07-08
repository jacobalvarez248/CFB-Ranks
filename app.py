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
    # ... existing code above remains
    # Ensure logo merge:
    if {"Team", "Image URL"}.issubset(logos_df.columns):
        logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
        df = df.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")
    # Build HTML table
    html_rank = [
        '<div style="max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>'
    ]
    # ... header construction
    html_rank.append('</tr></thead><tbody>')
    for _, row in df.iterrows():
        html_rank.append('<tr>')
        for c in cols_rank:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and str(logo).startswith("http"):
                    cell = f'<div style="display:flex; align-items:center;"><img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                else:
                    cell = v
            # ... other cases unchanged
            html_rank.append(f"<td style='{td_style}'>{cell}</td>")
        html_rank.append('</tr>')
    html_rank.append('</tbody></table></div>')
    st.markdown(''.join(html_rank), unsafe_allow_html=True)
(''.join(html_rank), unsafe_allow_html=True)

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
        if {"Conference", "Image URL"}.issubset(logos_df.columns):
            logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
            summary = summary.merge(
                logos_df[["Conference", "Logo URL"]], on="Conference", how="left"
            )
    except Exception:
        pass

    # Compute gradient bounds
    pr_min, pr_max = summary["Avg. Power Rating"].min(), summary["Avg. Power Rating"].max()
    agq_min, agq_max = summary["Avg. Game Quality"].min(), summary["Avg. Game Quality"].max()
    sdr_min, sdr_max = summary["Avg. Schedule Difficulty"].min(), summary["Avg. Schedule Difficulty"].max()

    # Build left summary table
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
        ) + (" white-space:nowrap; min-width:150px;" if c == "Conference" else "")
        html_conv.append(f"<th style='{th_style}'>{c}</th>")
    html_conv.append('</tr></thead><tbody>')
    for _, row in summary.iterrows():
        html_conv.append('<tr>')
        for c in conv_cols:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c == "Conference":
                logo = row.get("Logo URL")
                cell = (
                    f'<img src="{logo}" width="24" style="vertical-align:middle; margin-right:8px;">{v}'
                    if pd.notnull(logo) and str(logo).startswith("http") else v
                )
            elif c == "# Teams":
                cell = int(v)
            elif c in ["Avg. Power Rating", "Avg. Game Quality"]:
                t = (v - (pr_min if c == "Avg. Power Rating" else agq_min)) / ((pr_max if c == "Avg. Power Rating" else agq_max) - (pr_min if c == "Avg. Power Rating" else agq_min)) if ((pr_max if c == "Avg. Power Rating" else agq_max) > (pr_min if c == "Avg. Power Rating" else agq_min)) else 0
                rgb = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td_style += f" background-color:#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}; color:{'black' if t<0.5 else 'white'};"
                cell = f"{v:.1f}"
            else:
                inv = 1 - (v - sdr_min) / (sdr_max - sdr_min) if sdr_max > sdr_min else 1
                rgb = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                td_style += f" background-color:#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}; color:{'black' if inv<0.5 else 'white'};"
                cell = f"{v:.1f}"
            html_conv.append(f"<td style='{td_style}'>{cell}</td>")
        html_conv.append('</tr>')
    html_conv.append('</tbody></table></div>')

    # Scatterplot aside
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(''.join(html_conv), unsafe_allow_html=True)
    with col2:
        # Replace summary scatter with overall Power vs Game Quality scatter
        st.altair_chart(
            alt.Chart(df_expected).mark_circle(size=60, opacity=0.7).encode(
                x=alt.X("Average Game Quality", type="quantitative"),
                y=alt.Y("Power Rating", type="quantitative"),
                color="Conference:N",
                tooltip=["Team","Power Rating","Average Game Quality"]
            )
            .interactive()
            .properties(
                title="Power Rating vs Game Quality (All Teams)",
                height=600
            ),
            use_container_width=True
        )

    # Table underneath
    st.markdown("---")
    sel_conf = st.selectbox(
        "Select conference for details",
        options=summary["Conference"].tolist(),
        index=0,
    )
    df_conf = df_expected[df_expected["Conference"] == sel_conf].copy()
    if {"Team", "Image URL"}.issubset(logos_df.columns):
        logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
        df_conf = df_conf.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")
    df_conf = df_conf.sort_values("Projected Conference Wins", ascending=False)
    df_conf.insert(0, "Projected Conference Finish", list(range(1, len(df_conf) + 1)))

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
    for c in cols_conf:
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        ) + (" white-space:nowrap; min-width:200px;" if c == "Team" else "")
        html_conf.append(f"<th style='{th_style}'>{c}</th>")
    html_conf.append('</tr></thead><tbody>')
    for _, row in df_conf.iterrows():
        html_conf.append('<tr>')
        # Precompute gradient bounds for this conference
        qr_min, qr_max = df_conf["Projected Conference Wins"].min(), df_conf["Projected Conference Wins"].max()
        pr_min_c, pr_max_c = df_conf["Power Rating"].min(), df_conf["Power Rating"].max()
        agq_min_c, agq_max_c = df_conf["Average Game Quality"].min(), df_conf["Average Game Quality"].max()
        sdr_min_c, sdr_max_c = df_conf["Schedule Difficulty Rating"].min(), df_conf["Schedule Difficulty Rating"].max()
        for c in cols_conf:
            v = row[c]
            td_style = 'border:1px solid #ddd; padding:8px; text-align:center;'
            if c in ["Projected Conference Finish", "Preseason Rank"]:
                cell = int(v)
            elif c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and str(logo).startswith("http"):
                    cell = (
                        f'<div style="display:flex; align-items:center;">'
                        f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                    )
                else:
                    cell = v
            elif c in ["Projected Conference Wins", "Projected Conference Losses"]:
                cell = f"{v:.1f}"
            else:
                cell = f"{v:.1f}"
            html_conf.append(f"<td style='{td_style}'>{cell}</td>")(f"<td style='{td_style}'>{cell}</td>")
        html_conf.append('</tr>')
    html_conf.append('</tbody></table></div>')
    # Render detailed conference table
    st.markdown(''.join(html_conf), unsafe_allow_html=True)
