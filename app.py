
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
    cols_rank = (
        df.columns.tolist()[: df.columns.tolist().index("Schedule Difficulty Rating") + 1]
        if "Schedule Difficulty Rating" in df.columns else df.columns.tolist()
    )
    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    html = [
        '<div style="max-height:600px; overflow-y:auto;">',
        '<table style="width:100%; border-collapse:collapse;">',
        '<thead><tr>'
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

    # Rows
    for _, row in df.iterrows():
        html.append("<tr>")
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'

            if c == "Team":
                logo = row.get("Logo URL")
                if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                    cell = (
                        f'<div style="display:flex;align-items:center;">'
                        f'<img src="{logo}" width="24" style="margin-right:8px;"/>{v}</div>'
                    )
                else:
                    cell = v
            else:
                # existing branches
                if c == "OVER/UNDER Pick" and isinstance(v, str):
                    cell = v
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
        st.markdown("#### Conference Strength: Power Rating vs. Game Quality")
        import streamlit.components.v1 as components
        plot_df = summary.dropna(subset=["Logo URL"]).copy()
        scatter_html = """
        <div style='width:100%; max-width:700px; height:700px; position:relative;'>
            <svg width='100%' height='100%' viewBox='0 0 700 700'>
        """
        x_min, x_max = plot_df["Avg. Game Quality"].min(), plot_df["Avg. Game Quality"].max()
        y_min, y_max = plot_df["Avg. Power Rating"].min(), plot_df["Avg. Power Rating"].max()
        pad_x = (x_max - x_min) * 0.07
        pad_y = (y_max - y_min) * 0.09
        x_min, x_max = x_min - pad_x, x_max + pad_x
        y_min, y_max = y_min - pad_y, y_max + pad_y
        grid_fracs = [0, 0.2, 0.4, 0.6, 0.8, 1]
        for frac in grid_fracs:
            xpos = int(50 + 600 * frac)
            ypos = int(650 - 600 * frac)
            if frac not in [0, 1]:
                scatter_html += f'<line x1="{xpos}" y1="50" x2="{xpos}" y2="650" stroke="#ccc" stroke-width="1" stroke-dasharray="4"/>'
                scatter_html += f'<line x1="50" y1="{ypos}" x2="650" y2="{ypos}" stroke="#ccc" stroke-width="1" stroke-dasharray="4"/>'
        for _, row in plot_df.iterrows():
            x = int(50 + 600 * (row["Avg. Game Quality"] - x_min) / (x_max - x_min))
            y = int(650 - 600 * (row["Avg. Power Rating"] - y_min) / (y_max - y_min))
            logo_url = row["Logo URL"]
        if not (isinstance(logo_url, str) and logo_url.startswith("http")) or logo_url.strip() == "":
            logo_url = "https://png.pngtree.com/png-vector/20230115/ourmid/pngtree-american-football-nfl-rugby-ball-illustration-clipart-design-png-image_6564471.png"
        conf_name = row["Conference"]
        scatter_html += f'''
        <image href="{logo_url}" x="{x-14}" y="{y-14}" width="28" height="28">
            <title>{conf_name}</title>
        </image>
        '''
        scatter_html += '''
            <!-- X axis -->
            <line x1="50" y1="650" x2="650" y2="650" stroke="#002060" stroke-width="2"/>
            <rect x="240" y="660" width="220" height="30" fill="#002060"/>
            <text x="350" y="680" font-size="20" fill="#fff" font-weight="bold" text-anchor="middle">Avg. Game Quality</text>
            <!-- Y axis -->
            <line x1="50" y1="50" x2="50" y2="650" stroke="#002060" stroke-width="2"/>
            <rect x="-20" y="335" width="110" height="30" fill="#002060"/>
            <text x="10" y="355" font-size="20" fill="#fff" font-weight="bold" text-anchor="middle" transform="rotate(-90,10,355)">Avg. Power Rating</text>
        '''
        for frac in grid_fracs:
            xv = x_min + (x_max - x_min) * frac
            xpos = int(50 + 600 * frac)
            scatter_html += f'<text x="{xpos}" y="670" font-size="16" fill="#fff" font-weight="bold" text-anchor="middle">{xv:.1f}</text>'
            scatter_html += f'<line x1="{xpos}" y1="645" x2="{xpos}" y2="655" stroke="#002060" stroke-width="2"/>'
        for frac in grid_fracs:
            yv = y_min + (y_max - y_min) * frac
            ypos = int(650 - 600 * frac)
            scatter_html += f'<text x="30" y="{ypos+8}" font-size="16" fill="#fff" font-weight="bold" text-anchor="end">{yv:.1f}</text>'
            scatter_html += f'<line x1="45" y1="{ypos}" x2="55" y2="{ypos}" stroke="#002060" stroke-width="2"/>'
        scatter_html += """
            </svg>
        </div>
        """
        components.html(scatter_html, height=700)

    # --- Full-width detailed table below ---
    st.markdown("---")
    sel = st.selectbox("Select conference for details", summary["Conference"].tolist())
    df_conf = df_expected[df_expected["Conference"] == sel].copy()
    if "Projected Conference Wins" in df_conf.columns:
        df_conf = df_conf.sort_values(by="Projected Conference Wins", ascending=False).reset_index(drop=True)
    df_conf.insert(0, "Projected Conference Finish", range(1, len(df_conf) + 1))
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
        if c == "Team":
            th += " white-space:nowrap; min-width:200px;"
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
                if c == "Schedule Difficulty Rating":
                    t = 1 - t
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'white' if t>0.5 else 'black'};"
                cell = f"{v:.1f}"
            html_conf.append(f"<td style='{td}'>{cell}</td>")
        html_conf.append('</tr>')
    html_conf.append('</tbody></table></div>')
    st.markdown(''.join(html_conf), unsafe_allow_html=True)

