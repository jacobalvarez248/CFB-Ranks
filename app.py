import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import io
import numpy as np

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
df_schedule = load_sheet(data_path, "Schedule", header=0)
df_schedule.columns = df_schedule.columns.str.strip()

# Normalize logo column
logos_df["Team"] = logos_df["Team"].str.strip()
df_expected["Team"] = df_expected["Team"].str.strip()
if "Image URL" in logos_df.columns:
    logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)

team_logos = logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]].copy()
df_expected = df_expected.merge(team_logos, on="Team", how="left")
logos_df["Team"] = logos_df["Team"].astype(str).str.strip().str.upper()
df_expected["Conference"] = df_expected["Conference"].astype(str).str.strip().str.upper()

# --- Streamlit Config ---
import streamlit.components.v1 as components

FORCE_MOBILE = st.sidebar.checkbox("Mobile View", False)
def is_mobile():
    return FORCE_MOBILE

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
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected) + 1)))
if "Undefeated Probability" in df_expected.columns:
    df_expected["Undefeated Probability"] = (
        df_expected["Undefeated Probability"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notnull(x) else ""
        )
    )
drop_ranks = ["Preseason Rank", "Schedule Difficulty Rank", "Final 2024 Rank"]
numeric_cols = [c for c in df_expected.select_dtypes(include=["number"]).columns if c not in drop_ranks]
df_expected[numeric_cols] = df_expected[numeric_cols].round(1)
for col in ["Preseason Rank", "Final 2024 Rank"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').fillna(0).astype(int)
for col in ["Power Rating", "Average Game Quality", "Schedule Difficulty Rating"]:
    if col in df_expected.columns:
        df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').round(1)

# --- Sidebar & Tabs ---
tab = st.sidebar.radio(
    "Navigation",
    ["Rankings", "Conference Overviews", "Industry Composite Ranking", "Team Dashboards", "Charts & Graphs"]
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

    mobile_header_map = {
        "Preseason Rank": "Rank",
        "Team": "Team",
        "Power Rating": "Pwr. Rtg.",
        "Projected Overall Wins": "Proj. Wins",
        "Projected Overall Losses": "Proj. Losses",
        "OVER/UNDER Pick": "OVER/ UNDER",
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
        # Set min/max widths for compact columns on desktop
    compact_cols = [
        "Final 2024 Rank", "Preseason Rank", "Projected Overall Wins", "Projected Overall Losses",
        "Projected Conference Wins", "Projected Conference Losses", "Undefeated Probability",
        "Average Game Quality", "Schedule Difficulty Rank", "Schedule Difficulty Rating"
    ]
    for disp_col, c in zip(display_headers, cols_rank):
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            if is_mobile():
                th += " white-space:nowrap; min-width:48px; max-width:48px;"
            else:
                th += " white-space:nowrap; min-width:180px; max-width:280px;"
        elif not is_mobile() and c in compact_cols:
            th += " min-width:60px; max-width:72px; white-space:normal; font-size:13px; line-height:1.2;"
        else:
            th += " white-space:nowrap;"
        th += header_font
        html.append(f"<th style='{th}'>{disp_col}</th>")


    pr_min, pr_max = df["Power Rating"].min(), df["Power Rating"].max()
    agq_min, agq_max = df["Average Game Quality"].min(), df["Average Game Quality"].max()
    sdr_min, sdr_max = df["Schedule Difficulty Rating"].min(), df["Schedule Difficulty Rating"].max()

    for _, row in df.iterrows():
        html.append("<tr>")
        for c in cols_rank:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            td += cell_font
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

elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # --- Conference Summary Table ---
    conf_stats = (
        df_expected.groupby("Conference", as_index=False)
        .agg(
            Avg_Power_Rating=('Power Rating', 'mean'),
            Avg_Game_Quality=('Average Game Quality', 'mean'),
            Avg_Sched_Diff=('Schedule Difficulty Rating', 'mean')
        )
    )
    
    # Get logos for conferences
    conf_stats["Logo URL"] = conf_stats["Conference"].map(
        dict(zip(logos_df["Team"], logos_df["Logo URL"]))
    )

    # --- Clean up conference names for matching ---
    def clean_name(s):
        return str(s).strip().upper()
    
    conf_stats["Conference"] = conf_stats["Conference"].apply(clean_name)
    logos_df["Team"] = logos_df["Team"].apply(clean_name)
    
    # --- Build a unique logo map for conferences only ---
    # Option 1: If your logos_df includes conference rows (preferred)
    conf_logo_map = logos_df.drop_duplicates("Team").set_index("Team")["Logo URL"].to_dict()
    
    # Option 2: If you have a separate conference logo sheet, use that instead
    
    # --- Attach logos to each conference ---
    conf_stats["Logo URL"] = conf_stats["Conference"].map(conf_logo_map)
    
    # --- Check for missing or duplicate logo URLs ---
    dupe_urls = conf_stats["Logo URL"].value_counts()
    dupes = dupe_urls[dupe_urls > 1]
    if not dupes.empty:
        st.warning("Duplicate logo URLs used by: " +
                   ", ".join([f"{url} ({count}x)" for url, count in dupes.items()]))
    
    missing = conf_stats[conf_stats["Logo URL"].isnull()]["Conference"].tolist()
    if missing:
        st.warning("Missing logo for: " + ", ".join(missing))
    
    # --- Only plot valid, unique conference points ---
    conf_stats_plot = conf_stats.dropna(subset=["Avg_Power_Rating", "Avg_Game_Quality", "Logo URL"])
    conf_stats_plot = conf_stats_plot.drop_duplicates(subset=["Logo URL"])
    
    # --- Set axis and image sizes ---
    logo_size = 28
    scatter_height = 470
    font_size = 15
    x_min = float(conf_stats_plot["Avg_Game_Quality"].min()) - 1
    x_max = float(conf_stats_plot["Avg_Game_Quality"].max()) + 0.3
    
    # --- Altair Scatter Plot ---
    import altair as alt

    logo_size = 28  # Or your preferred size
    scatter_height = 470  # Taller than before
    font_size = 15
    x_min = float(conf_stats_plot["Avg_Game_Quality"].min()) - 1
    x_max = float(conf_stats_plot["Avg_Game_Quality"].max()) + 0.3
    
    chart = alt.Chart(conf_stats_plot).mark_image(
        width=logo_size,
        height=logo_size
    ).encode(
        x=alt.X(
            'Avg_Game_Quality:Q',
            scale=alt.Scale(domain=[x_min, x_max]),
            axis=alt.Axis(
                title='Average Game Quality',
                titleFontSize=font_size + 2,
                labelFontSize=font_size,
                labelColor='black',
                titleColor='black'
            )
        ),
        y=alt.Y(
            'Avg_Power_Rating:Q',
            axis=alt.Axis(
                title='Average Power Rating',
                titleFontSize=font_size + 2,
                labelFontSize=font_size,
                labelColor='black',
                titleColor='black'
            )
        ),
        url='Logo URL:N',
        tooltip=[
            'Conference',
            alt.Tooltip('Avg_Power_Rating', format=".2f"),
            alt.Tooltip('Avg_Game_Quality', format=".2f")
        ]
    ).properties(
        height=scatter_height,
        width='container',
        title=""
    )
    chart = chart.configure_axis(
        labelColor='black',
        titleColor='black',
        gridColor='#eaeaea'
    ).configure_title(
        color='black'
    ).configure_legend(
        labelColor='black',
        titleColor='black'
    ).configure_view(
        strokeWidth=0
    )


    # Responsive headers/styles
    if is_mobile():
        summary_headers = ["Conference", "Avg. Pwr. Rtg.", "Avg. Game Qty", "Avg. Sched. Diff."]
        summary_cols = ["Conference", "Avg_Power_Rating", "Avg_Game_Quality", "Avg_Sched_Diff"]
        table_style = "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
        wrapper_style = "max-width:100vw; overflow-x:hidden; margin:0 -16px 8px -16px;"
        header_font = "font-size:13px; white-space:normal;"
        cell_font = "font-size:13px; white-space:nowrap;"
    else:
        summary_headers = ["Conference", "Average Power Rating", "Average Game Quality", "Average Schedule Difficulty"]
        summary_cols = ["Conference", "Avg_Power_Rating", "Avg_Game_Quality", "Avg_Sched_Diff"]
        table_style = "width:100%; border-collapse:collapse;"
        wrapper_style = "max-width:100%; overflow-x:auto; margin-bottom:16px;"
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"
    
    pr_min, pr_max = conf_stats["Avg_Power_Rating"].min(), conf_stats["Avg_Power_Rating"].max()
    gq_min, gq_max = conf_stats["Avg_Game_Quality"].min(), conf_stats["Avg_Game_Quality"].max()
    sd_min, sd_max = conf_stats["Avg_Sched_Diff"].min(), conf_stats["Avg_Sched_Diff"].max()
    
    def cell_color(val, col_min, col_max, inverse=False):
        try:
            v = float(val)
        except Exception:
            return ""
        t = (v - col_min) / (col_max - col_min) if col_max > col_min else 0
        if inverse:
            t = 1 - t
        r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
        return f"background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t < 0.5 else 'white'}; font-weight:600;"
    
    html = [f'<div style="{wrapper_style}"><table style="{table_style}"><thead><tr>']
    for h in summary_headers:
        html.append(
            f'<th style="border:1px solid #ddd; padding:8px; background-color:#002060; color:white; text-align:center; {header_font}">{h}</th>'
        )
    html.append('</tr></thead><tbody>')
    
    for _, row in conf_stats.iterrows():
        html.append('<tr>')
        # Conference Logo (logo only on mobile, logo+name on desktop)
        logo_url = row["Logo URL"]
        logo_width = 28 if is_mobile() else 24
        if pd.notnull(logo_url) and isinstance(logo_url, str) and logo_url.startswith("http"):
            logo_html = f'<img src="{logo_url}" width="{logo_width}" style="display:inline-block;vertical-align:middle; margin-right:7px;" />'
        else:
            logo_html = ""
        if is_mobile():
            conf_cell = logo_html
        else:
            conf_cell = f"{logo_html}{row['Conference']}"
        html.append(f'<td style="border:1px solid #ddd; text-align:left; {cell_font}">{conf_cell}</td>')
    
        # Avg Power Rating
        pr_style = cell_color(row["Avg_Power_Rating"], pr_min, pr_max)
        html.append(f'<td style="border:1px solid #ddd; text-align:center; {cell_font}{pr_style}">{row["Avg_Power_Rating"]:.1f}</td>')
    
        # Avg Game Quality
        gq_style = cell_color(row["Avg_Game_Quality"], gq_min, gq_max)
        html.append(f'<td style="border:1px solid #ddd; text-align:center; {cell_font}{gq_style}">{row["Avg_Game_Quality"]:.1f}</td>')
    
        # Avg Sched Diff (inverse color scale)
        sd_style = cell_color(row["Avg_Sched_Diff"], sd_min, sd_max, inverse=True)
        html.append(f'<td style="border:1px solid #ddd; text-align:center; {cell_font}{sd_style}">{row["Avg_Sched_Diff"]:.1f}</td>')
    
        html.append('</tr>')
    html.append('</tbody></table></div>')

    # Only keep rows with valid numeric values for plotting
    conf_stats_plot = conf_stats.dropna(subset=["Avg_Power_Rating", "Avg_Game_Quality", "Logo URL"])
    # -- Add these lines before your chart code --
    logo_size = 26         # or adjust to 22, 24, etc. for preferred icon size
    scatter_height = 380   # or whatever height looks good for your layout
    font_size = 15
    
    x_min = float(conf_stats_plot["Avg_Game_Quality"].min()) - 1
    x_max = float(conf_stats_plot["Avg_Game_Quality"].max()) + 0.3

    # Ensure all numbers are floats, coerce errors to NaN
    for col in ["Avg_Power_Rating", "Avg_Game_Quality", "Avg_Sched_Diff"]:
        conf_stats[col] = pd.to_numeric(conf_stats[col], errors="coerce")
    
    # Filter for only valid data
    conf_stats_plot = conf_stats.dropna(subset=["Avg_Power_Rating", "Avg_Game_Quality", "Logo URL"])
    conf_stats_plot = conf_stats_plot[
        conf_stats_plot["Logo URL"].astype(str).str.startswith("http")
    ]
    
    # Optional debug: show which are still missing
    missing_plot = conf_stats[
        conf_stats[["Avg_Power_Rating", "Avg_Game_Quality", "Logo URL"]].isnull().any(axis=1) |
        ~conf_stats["Logo URL"].astype(str).str.startswith("http")
    ]["Conference"].tolist()
    if missing_plot:
        st.warning("Conferences not plotted: " + ", ".join(missing_plot))

    # ---- CHART CODE (scatterplot) ----
    chart = alt.Chart(conf_stats_plot).mark_image(
        width=logo_size,
        height=logo_size
    ).encode(
        x=alt.X(
            'Avg_Game_Quality:Q',
            scale=alt.Scale(domain=[x_min, x_max]),
            axis=alt.Axis(
                title='Average Game Quality',
                titleFontSize=font_size+2,
                labelFontSize=font_size
            )
        ),
        y=alt.Y(
            'Avg_Power_Rating:Q',
            axis=alt.Axis(
                title='Average Power Rating',
                titleFontSize=font_size+2,
                labelFontSize=font_size
            )
        ),
        url='Logo URL:N',
        tooltip=[
            'Conference',
            alt.Tooltip('Avg_Power_Rating', format=".2f"),
            alt.Tooltip('Avg_Game_Quality', format=".2f")
        ]
    ).properties(
        height=scatter_height,
        width='container',
        title=""
    )

    # ---- RENDER: Desktop (table left, chart right); Mobile (table only) ----
    if is_mobile():
        st.markdown("#### Conference Summary")
        st.markdown("".join(html), unsafe_allow_html=True)
        # No chart on mobile
    else:
        left, right = st.columns([1, 1])
        with left:
            st.markdown("#### Conference Summary")
            st.markdown("".join(html), unsafe_allow_html=True)
        with right:
            st.markdown("#### Power Rating vs Game Quality")
            st.altair_chart(chart, use_container_width=True)
   
    # --- Conference Standings Table ---
    st.markdown("#### Conference Standings")
    conference_options = sorted(df_expected["Conference"].dropna().unique())
    selected_conf = st.selectbox("Select Conference", conference_options, index=0)
    standings = df_expected[df_expected["Conference"] == selected_conf].copy()
    standings = standings.sort_values(
        by="Projected Conference Wins", ascending=False
    ).reset_index(drop=True)
    standings.insert(0, "Projected Finish", standings.index + 1)

    mobile_header_map = {
        "Projected Finish": "Conf. Standings",
        "Team": "Team",
        "Power Rating": "Pwr. Rtg.",
        "Projected Overall Wins": "Proj. Wins",
        "Projected Conference Wins": "Proj. Conf. Wins",
        "Projected Conference Losses": "Proj. Conf. Losses",
        "Average Conference Game Quality": "Avg. Conf. Game Qty",
        "Schedule Difficulty Rank": "Sched. Diff. Rk",
        "Average Conference Schedule Difficulty": "Conf. Sched. Diff.",
    }
    mobile_cols = [
        "Projected Finish", "Team", "Power Rating", "Projected Overall Wins",
        "Projected Conference Wins", "Projected Conference Losses",
        "Average Conference Game Quality", "Average Conference Schedule Difficulty"
    ]
    desktop_cols = [
        "Projected Finish", "Team", "Power Rating", "Projected Overall Wins",
        "Projected Conference Wins", "Projected Conference Losses",
        "Average Conference Game Quality", "Schedule Difficulty Rank", "Average Conference Schedule Difficulty"
    ]
    pr_min, pr_max = standings["Power Rating"].min(), standings["Power Rating"].max()
    acgq_min, acgq_max = standings["Average Conference Game Quality"].min(), standings["Average Conference Game Quality"].max()
    acsd_min, acsd_max = standings["Average Conference Schedule Difficulty"].min(), standings["Average Conference Schedule Difficulty"].max()

    if is_mobile():
        cols = [c for c in mobile_cols if c in standings.columns]
        display_headers = [mobile_header_map[c] for c in cols]
        table_style = (
            "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
        )
        wrapper_style = (
            "max-width:100vw; overflow-x:hidden; margin:0 -16px 0 -16px;"
        )
        header_font = "font-size:13px; white-space:normal;"
        cell_font = "font-size:13px; white-space:nowrap;"
    else:
        cols = [c for c in desktop_cols if c in standings.columns]
        display_headers = cols.copy()
        table_style = "width:100%; border-collapse:collapse;"
        wrapper_style = "max-width:100%; overflow-x:auto;"
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"

    html = [
        f'<div style="{wrapper_style}">',
        f'<table style="{table_style}">',
        '<thead><tr>'
    ]
    compact_cols_conf = [
        "Projected Finish", "Power Rating", "Projected Overall Wins", "Projected Conference Wins",
        "Projected Conference Losses", "Average Conference Game Quality",
        "Schedule Difficulty Rank", "Average Conference Schedule Difficulty"
    ]
    for disp_col, c in zip(display_headers, cols):
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; '
            'background-color:#002060; color:white; position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            if is_mobile():
                th += " white-space:nowrap; min-width:48px; max-width:48px;"
            else:
                th += " white-space:nowrap; min-width:180px; max-width:240px;"
        elif not is_mobile() and c in compact_cols_conf:
            th += " min-width:60px; max-width:72px; white-space:normal; font-size:13px; line-height:1.2;"
        else:
            th += " white-space:nowrap;"
        th += header_font
        html.append(f"<th style='{th}'>{disp_col}</th>")
    html.append("</tr></thead><tbody>")
    for _, row in standings.iterrows():
        html.append("<tr>")
        for c in cols:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            td += cell_font
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
                if c == "Power Rating" and pd.notnull(v):
                    t = (v - pr_min) / (pr_max - pr_min) if pr_max > pr_min else 0
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                elif c == "Average Conference Game Quality" and pd.notnull(v):
                    t = (v - acgq_min) / (acgq_max - acgq_min) if acgq_max > acgq_min else 0
                    r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                elif c == "Average Conference Schedule Difficulty" and pd.notnull(v):
                    inv = 1 - ((v - acsd_min) / (acsd_max - acsd_min) if acsd_max > acsd_min else 0)
                    r, g, b = [int(255 + (x - 255) * inv) for x in (0, 32, 96)]
                    td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if inv<0.5 else 'white'};"
                    cell = f"{v:.1f}"
                else:
                    cell = v
            html.append(f"<td style='{td}'>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

elif tab == "Industry Composite Ranking":
    st.header("📊 Industry Composite Ranking")

    # Load and clean data
    df_comp = load_sheet(data_path, "Industry Composite", header=0)
    df_comp.columns = [str(c).strip() for c in df_comp.columns]
    logos_df["Team"] = logos_df["Team"].astype(str)
    df_comp["Team"] = df_comp["Team"].astype(str)

    # --- Clean team names: remove leading/trailing/multiple spaces, uppercase ---
    def clean_team_name(name):
        if pd.isnull(name):
            return ""
        return " ".join(str(name).strip().upper().split())

    logos_df["Team"] = logos_df["Team"].apply(clean_team_name)
    df_comp["Team"] = df_comp["Team"].apply(clean_team_name)

    # --- Merge in Logo URL ---
    df_comp = df_comp.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")

    # --- Optional: warn if missing logos ---
    missing_logos = df_comp[df_comp["Logo URL"].isna()]["Team"].tolist()
    if missing_logos:
        st.warning(f"Missing logos for: {', '.join(missing_logos[:7])}{'...' if len(missing_logos) > 7 else ''}")

    # --- Column setup ---
    all_metrics = ["Composite", "JPR", "SP+", "FPI", "Kford"]

    if is_mobile():
        main_cols = ["Composite Rank", "Team"] + all_metrics
        mobile_header_map = {
            "Composite Rank": "Rank",
            "Team": "Team",
            "Composite": "Comp.",
            "JPR": "JPR",
            "SP+": "SP+",
            "FPI": "FPI",
            "Kford": "Kford"
        }
        display_headers = [mobile_header_map.get(c, c) for c in main_cols]
    else:
        main_cols = ["Composite Rank", "Team", "Conference"] + all_metrics
        desktop_header_map = {
            "Composite Rank": "Rank",
            "Team": "Team",
            "Conference": "Conference",
            "Composite": "Composite",
            "JPR": "JPR",
            "SP+": "SP+",
            "FPI": "FPI",
            "Kford": "Kford"
        }
        display_headers = [desktop_header_map.get(c, c) for c in main_cols]

    display_cols = [c for c in main_cols if c in df_comp.columns]

    # --- Sidebar filters ---
    team_filter = st.sidebar.text_input("Filter by team...", "")
    conf_filter = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", display_cols, display_cols.index("Composite Rank") if "Composite Rank" in display_cols else 0
    )
    asc = st.sidebar.checkbox("Ascending order", False)

    df_show = df_comp.copy()
    if team_filter:
        df_show = df_show[df_show["Team"].str.contains(team_filter.strip().upper(), case=False, na=False)]
    if conf_filter and "Conference" in df_show.columns:
        df_show = df_show[df_show["Conference"].str.contains(conf_filter.strip().upper(), case=False, na=False)]
    # Always sort by the selected column
    df_show = df_show.sort_values(by=sort_col, ascending=asc if sort_col != "Composite Rank" else True)

    metric_cols = [c for c in all_metrics if c in df_show.columns]
    composite_min, composite_max = df_show["Composite"].min(), df_show["Composite"].max()
    other_metric_cols = [c for c in metric_cols if c != "Composite"]
    col_min = {c: df_show[c].min() for c in other_metric_cols}
    col_max = {c: df_show[c].max() for c in other_metric_cols}

    # --- Table styling ---
    if is_mobile():
        table_style = (
            "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
        )
        wrapper_style = (
            "max-width:100vw; overflow-x:hidden; margin:0 -16px 0 -16px;"
        )
        header_font = "font-size:13px; white-space:normal;"
        cell_font = "font-size:13px; white-space:nowrap;"
    else:
        table_style = "width:100%; border-collapse:collapse;"
        wrapper_style = "max-width:100%; overflow-x:auto;"
        header_font = ""
        cell_font = "white-space:nowrap; font-size:15px;"

    html = [
        f'<div style="{wrapper_style}">',
        f'<table style="{table_style}">',
        '<thead><tr>'
    ]
    compact_cols = ["Composite Rank", "Conference", "Composite", "JPR", "SP+", "FPI", "Kford"]

    for disp_col, c in zip(display_headers, display_cols):
        if c == "Composite":
            th = (
                'border:1px solid #ddd; padding:8px; text-align:center; background-color:#548235; color:white; '
                'position:sticky; top:0; z-index:2;'
            )
        else:
            th = (
                'border:1px solid #ddd; padding:8px; text-align:center; background-color:#002060; color:white; '
                'position:sticky; top:0; z-index:2;'
            )
        if c == "Team":
            if is_mobile():
                th += " white-space:nowrap; min-width:60vw; max-width:80vw;"
            else:
                th += " white-space:nowrap; min-width:180px; max-width:260px;"
        elif is_mobile() and c in all_metrics:
            th += " min-width:38px; max-width:50px; white-space:normal; font-size:12px; line-height:1.1;"
        elif not is_mobile() and c in compact_cols:
            th += " min-width:60px; max-width:72px; white-space:normal; font-size:13px; line-height:1.2;"
        else:
            th += " white-space:nowrap;"
        th += header_font
        html.append(f"<th style='{th}'>{disp_col}</th>")
    html.append("</tr></thead><tbody>")

    for _, row in df_show.iterrows():
        # Find the highest and lowest among JPR, SP+, FPI, Kford for this row
        highlight_metrics = [col for col in ["JPR", "SP+", "FPI", "Kford"] if col in df_show.columns]
        values = {col: row[col] for col in highlight_metrics if pd.notnull(row[col])}
        high_val = max(values.values()) if values else None
        low_val = min(values.values()) if values else None

        html.append("<tr>")
        for c in display_cols:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            td += cell_font
            if is_mobile() and c in all_metrics:
                td += " font-size:12px; padding:4px;"
            cell = v
            if c == "Team":
                logo = row.get("Logo URL")
                # MOBILE: logo only; DESKTOP: logo+name
                if is_mobile():
                    if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                        cell = f'<img src="{logo}" width="32" style="margin:0 auto; display:block;"/>'
                    else:
                        cell = ""
                else:
                    team_name = v
                    if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                        cell = (
                            f'<div style="display:flex;align-items:center;">'
                            f'<img src="{logo}" width="24" style="margin-right:8px;"/>{team_name}</div>'
                        )
                    else:
                        cell = team_name
            elif c == "Composite Rank":
                cell = f"{int(v)}"
            elif c == "Composite" and pd.notnull(v):
                # Green color scale (light gray to #548235)
                t = (v - composite_min) / (composite_max - composite_min) if composite_max > composite_min else 0
                r1, g1, b1 = 234, 234, 234  # light gray
                r2, g2, b2 = 84, 130, 53    # #548235
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                yiq = ((r*299)+(g*587)+(b*114))/1000
                text_color = "black" if yiq > 140 else "white"
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{text_color}; font-weight:bold;"
                cell = f"<b>{v:.1f}</b>"
            elif c in other_metric_cols and pd.notnull(v):
                mn, mx = col_min[c], col_max[c]
                t = (v - mn) / (mx - mn) if mx > mn else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                if c in ["JPR", "SP+", "FPI", "Kford"]:
                    if high_val is not None and abs(v - high_val) < 1e-8:
                        cell = f"<b>{v:.1f}</b>"
                    elif low_val is not None and abs(v - low_val) < 1e-8:
                        td += " color:#d2222a;"  # a strong red, change as desired
                        cell = f"{v:.1f}"
                    else:
                        cell = f"{v:.1f}"
                else:
                    cell = f"{v:.1f}"
            else:
                cell = v
            html.append(f"<td style='{td}'>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


elif tab == "Team Dashboards":
    st.header("🏈 Team Dashboards")

    team_options = df_expected["Team"].sort_values().unique().tolist()
    selected_team = st.selectbox("Select Team", team_options, index=0, key="team_dash_select")
    team_row = df_expected[df_expected["Team"] == selected_team].iloc[0]
    logo_url = team_row["Logo URL"] if "Logo URL" in team_row and pd.notnull(team_row["Logo URL"]) else None
    # ADD THIS BACK
    conference = team_row["Conference"] if "Conference" in team_row else ""
    conf_logo_url = None
    if conference in logos_df["Team"].values:
        conf_logo_url = logos_df.loc[logos_df["Team"] == conference, "Logo URL"].values[0]
    
    # 1. Get overall rank from Expected Wins sheet
    overall_rank = int(team_row["Preseason Rank"]) if "Preseason Rank" in team_row else None
    
    # 2. Calculate conference rank (by Power Rating)
    conf_teams = df_expected[df_expected["Conference"] == conference].copy()
    conf_teams = conf_teams.sort_values("Power Rating", ascending=False)
    conf_teams["Conf Rank"] = range(1, len(conf_teams) + 1)
    this_conf_rank = conf_teams.loc[conf_teams["Team"] == selected_team, "Conf Rank"].values[0] if not conf_teams.empty else None
    
    # Mobile label
    conf_rank_label = "Conf. Rk" if not is_mobile() else "Conf. Rk"
    
    # --- Card styling ---
    card_style = (
        "display:inline-flex; flex-direction:column; align-items:center; justify-content:center; "
        "background:#002060; border:1px solid #FFFFFF; border-radius:10px; margin-right:10px; min-width:48px; "
        "height:48px; width:48px; font-size:15px; font-weight:700; color:#FFFFFF; text-align:center;"
        if not is_mobile() else
        "display:inline-flex; flex-direction:column; align-items:center; justify-content:center; "
        "background:#002060; border:1px solid #FFFFFF; border-radius:7px; margin-right:7px; min-width:28px; "
        "height:28px; width:28px; font-size:10px; font-weight:700; color:#FFFFFF; text-align:center;"
    )
    lighter_card_style = (
        "display:inline-flex; flex-direction:column; align-items:center; justify-content:center; "
        "background:#6ea2e7; border:1px solid #FFFFFF; border-radius:10px; margin-right:10px; min-width:48px; "
        "height:48px; width:48px; font-size:15px; font-weight:700; color:#FFFFFF; text-align:center;"
        if not is_mobile() else
        "display:inline-flex; flex-direction:column; align-items:center; justify-content:center; "
        "background:#6ea2e7; border:1px solid #FFFFFF; border-radius:10px; margin-right:10px; min-width:48px; "
        "height:48px; width:48px; font-size:15px; font-weight:700; color:#FFFFFF; text-align:center;"
    )

    logo_dim = 48 if not is_mobile() else 28
   
    # ---- Team Schedule Table ----
    team_col = [col for col in df_schedule.columns if "Team" in col][0]
    sched = df_schedule[df_schedule[team_col] == selected_team].copy()

    # === CALCULATE FINAL WIN DISTRIBUTION ===
    
    # 1. Get opponent list and number of games
    opponents = sched["Opponent"].tolist()
    num_games = len(opponents)
    
    # 2. Set up win probability list from schedule (defaults to 0.5 if missing)
    if "Win Probability" in sched.columns:
        win_prob_list = sched["Win Probability"].astype(float).values
    elif "Win Prob" in sched.columns:
        win_prob_list = sched["Win Prob"].astype(float).values
    else:
        win_prob_list = np.full(num_games, 0.5)  # fallback
    
    # 3. Dynamic programming: build win distribution table
    dp = np.zeros((num_games + 1, num_games + 1))
    dp[0, 0] = 1.0
    for g in range(1, num_games + 1):
        p = win_prob_list[g-1]
        for w in range(g+1):
            win_part = dp[g-1, w-1] * p if w > 0 else 0
            lose_part = dp[g-1, w] * (1 - p)
            dp[g, w] = win_part + lose_part
    
    # 4. Compute final win distribution (probability of exactly w wins)
    win_probs = dp[num_games, :]  # shape: (num_games+1,)
    
    # 5. Calculate "at least" and "exactly" win probabilities for cards
    at_least_6 = win_probs[6:].sum() if len(win_probs) > 6 else 0.0
    at_least_8 = win_probs[8:].sum() if len(win_probs) > 8 else 0.0
    at_least_10 = win_probs[10:].sum() if len(win_probs) > 10 else 0.0
    # "12-0" card should always be exactly 12 wins, but handle if fewer games
    if len(win_probs) > 12:
        exact_12 = win_probs[12]
    elif len(win_probs) == 12:
        exact_12 = win_probs[-1]
    else:
        exact_12 = 0.0
    
    at_least_6_pct = f"{at_least_6*100:.1f}%"
    at_least_8_pct = f"{at_least_8*100:.1f}%"
    at_least_10_pct = f"{at_least_10*100:.1f}%"
    exact_12_pct = f"{exact_12*100:.1f}%"
    
    # 6. Render stat cards (single row, includes logo, rank, conf rank, win cards)
    card_html = f'''
    <div style="display: flex; align-items: center; gap:14px; margin-top:8px; margin-bottom:10px;">
        <img src="{logo_url}" width="{logo_dim}" style="display:inline-block;"/>
        {f"<img src='{conf_logo_url}' width='{logo_dim}' style='display:inline-block;'/>" if conf_logo_url else ""}
        <div style="{card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">Rank</span>
            <span style="line-height:1.15;">{overall_rank}</span>
        </div>
        <div style="{card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">Conf. Rk</span>
            <span style="line-height:1.15;">{this_conf_rank}</span>
        </div>
        <div style="{lighter_card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">6-6+</span>
            <span style="line-height:1.15; font-weight:bold;">{at_least_6_pct}</span>
        </div>
        <div style="{lighter_card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">8-4+</span>
            <span style="line-height:1.15; font-weight:bold;">{at_least_8_pct}</span>
        </div>
        <div style="{lighter_card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">10-2+</span>
            <span style="line-height:1.15; font-weight:bold;">{at_least_10_pct}</span>
        </div>
        <div style="{lighter_card_style}">
            <span style="font-size:0.75em; color:#FFF; font-weight:400;">12-0</span>
            <span style="line-height:1.15; font-weight:bold;">{exact_12_pct}</span>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)
    
    # 7. For schedule table rendering (and your "rows" for win progression), guard index!
    rows = []
    for g in range(1, num_games + 1):
        opp = opponents[g-1] if (g-1) < len(opponents) else ""
        row = {
            "Game": g,
            "Opponent": opp
        }
        for w in range(num_games + 1):
            row[w] = dp[g, w]
        rows.append(row)

    # --- (Rest of your schedule table code here; you can keep your existing mobile/desktop rendering logic) ---
    if not sched.empty:
        sched["Date"] = pd.to_datetime(sched["Date"]).dt.strftime("%b-%d")

        def format_opp_rank(x):
            if pd.isnull(x):
                return ""
            try:
                val = float(x)
                return "FCS" if val <= 0 else f"{int(round(val))}"
            except Exception:
                return str(x)

        sched["Opponent Rank"] = sched["Opponent Ranking"].apply(format_opp_rank)
        def fmt_spread(x):
            if pd.isnull(x):
                return ""
            val = -round(x * 2) / 2
            if val > 0:
                return f"+{val:.1f}"
            else:
                return f"{val:.1f}"
        sched["Projected Spread"] = sched["Spread"].apply(fmt_spread)
        sched["Win Probability"] = sched["Win Prob"].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "")
        sched["Game Quality"] = sched["Game Score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "")

        # MOBILE header/column maps
        mobile_headers = {
            "Date": "Date",
            "Opponent": "Opp.",
            "Opponent Rank": "Opp. Rank",
            "Projected Spread": "Proj. Spread",
            "Win Probability": "Win Prob.",
            "Game Quality": "Game Qty"
        }
        mobile_cols = list(mobile_headers.keys())

        # DESKTOP version (original)
        desktop_headers = ["Game", "Date", "Opponent", "Opponent Rank", "Projected Spread", "Win Probability", "Game Quality"]

        # Choose headers/columns based on device
        if is_mobile():
            headers = [mobile_headers[c] for c in mobile_cols]
            use_cols = mobile_cols
            table_style = (
                "width:100vw; max-width:100vw; border-collapse:collapse; table-layout:fixed; font-size:13px;"
            )
            wrapper_style = (
                "max-width:100vw; overflow-x:hidden; margin:0 -16px 0 -16px;"
            )
            header_font = "font-size:13px; white-space:normal;"
            cell_font = "font-size:13px; white-space:nowrap;"
        else:
            headers = desktop_headers
            use_cols = desktop_headers
            table_style = "width:100%; border-collapse:collapse;"
            wrapper_style = "max-width:100%; overflow-x:auto;"
            header_font = ""
            cell_font = "white-space:nowrap; font-size:15px;"

        gq_vals = pd.to_numeric(sched["Game Quality"], errors='coerce')
        gq_min, gq_max = gq_vals.min(), gq_vals.max()

        def win_prob_data_bar(pct_str):
            try:
                pct = float(pct_str.strip('%'))
                bar_width = pct
                return (
                    f'<div style="width:100%; text-align:center; font-weight:600; color:#111;">{pct_str}</div>'
                    f'<div style="background:#d6eaff; width:100%; height:13px; border-radius:4px; margin-top:-2px;">'
                    f'<div style="background:#007bff; width:{bar_width}%; height:13px; border-radius:4px;"></div>'
                    f'</div>'
                )
            except Exception:
                return f'<div style="width:100%; text-align:center; font-weight:600; color:#111;">{pct_str}</div>'

        header_style = (
            "background-color:#002060; color:white; text-align:center; padding:8px; "
            "position:sticky; top:0; z-index:2; font-weight:bold;"
        )
        cell_style = "border:1px solid #ddd; padding:8px; text-align:center;"

        html = [
            f'<div style="{wrapper_style}">',
            f'<table style="{table_style}">',
            '<thead><tr>'
        ]
        for i, h in enumerate(headers):
            # Wider "Opp." column on mobile
            if is_mobile() and h == "Opp.":
                html.append(f'<th style="{header_style}{header_font} min-width:30vw; max-width:38vw; word-break:break-word;">{h}</th>')
            elif is_mobile():
                html.append(f'<th style="{header_style}{header_font} min-width:11vw; max-width:19vw;">{h}</th>')
            else:
                html.append(f'<th style="{header_style}{header_font}">{h}</th>')
        html.append('</tr></thead><tbody>')

        for _, row in sched.iterrows():
            html.append('<tr>')
            for col in use_cols:
                val = row[col]
                style = cell_style + cell_font + "padding:4px;"
                if is_mobile() and col == "Opponent":
                    style += "min-width:30vw; max-width:38vw; word-break:break-word; font-size:11px;"
                elif is_mobile():
                    style += "min-width:11vw; max-width:19vw; font-size:11px;"
                # Projected Spread styling
                if col == "Projected Spread":
                    try:
                        val_float = float(val)
                        if val_float < 0:
                            style += "background-color:#004085; color:white; font-weight:bold;"
                        elif val_float > 0:
                            style += "background-color:#a71d2a; color:white; font-weight:bold;"
                    except Exception:
                        pass
                # Win Probability: text above the bar, black text
                if col == "Win Probability":
                    val = win_prob_data_bar(val)
                    html.append(f'<td style="position:relative; {style} width:90px; min-width:70px; max-width:120px; vertical-align:middle;">{val}</td>')
                    continue
                # Game Quality: blue color scale background, same as Power Rating
                if col == "Game Quality":
                    try:
                        v = float(val)
                        t = (v - gq_min) / (gq_max - gq_min) if gq_max > gq_min else 0
                        r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                        style += f"background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'}; font-weight:600;"
                    except Exception:
                        pass

                html.append(f'<td style="{style}">{val}</td>')
            html.append('</tr>')
        html.append('</tbody></table></div>')

        st.markdown("".join(html), unsafe_allow_html=True)

    # Add all team-specific tables/charts below as needed
    # --- Opponent logos (above the table rendering) ---
    fallback_logo_url = "https://upload.wikimedia.org/wikipedia/en/thumb/d/d4/NCAA_Division_I_FCS_logo.svg/250px-NCAA_Division_I_FCS_logo.svg.png"
    opponent_logos = []
    for opp in opponents:
        logo_url = fallback_logo_url
        try:
            matches = logos_df["Team"].str.lower() == str(opp).strip().lower()
            if matches.any():
                logo_url = logos_df.loc[matches, "Logo URL"].values[0]
        except Exception:
            pass
        opponent_logos.append(logo_url)

    # --- Unified Responsive Table Block ---
    n_cols = 2 + num_games + 1  # Game + Opp + win columns
    col_pct = 100 / n_cols

    if is_mobile():
        font_size = 6
        pad = 0
        logo_size = 10
        table_style = (
            f"font-size:{font_size}px; width:100%; min-width:100%; max-width:100%; "
            "table-layout:fixed; border-collapse:collapse; border:none; margin:0; box-sizing:border-box;"
        )
        wrapper_style = (
            "width:100%; min-width:100%; max-width:100%; margin:0; padding:0; overflow:hidden; box-sizing:border-box;"
        )
        visible_wins = list(range(num_games + 1))
        cell_base_style = (
            f"padding:{pad}px; box-sizing:border-box; "
            f"width:{col_pct:.6f}%; min-width:{col_pct:.6f}%; max-width:{col_pct:.6f}%; "
            "overflow:hidden; white-space:nowrap; border-right:0.5px solid #bbb; border-bottom:0.5px solid #bbb;"
        )
        cell_last_style = (
            f"padding:{pad}px; box-sizing:border-box; "
            f"width:{col_pct:.6f}%; min-width:{col_pct:.6f}%; max-width:{col_pct:.6f}%; "
            "overflow:hidden; white-space:nowrap; border-bottom:0.5px solid #bbb;"
        )
        game_col_style = cell_base_style
        opp_col_style = cell_base_style
        win_col_style = cell_base_style
    else:
        font_size = 12
        pad = 2
        logo_size = 26
        n_win_cols = num_games + 1
        opp_col_pct = 20
        game_col_pct = 7
        win_col_pct = (100 - opp_col_pct - game_col_pct) / n_win_cols
        table_style = (
            "font-size:12px; width:100%; border-collapse:collapse; table-layout:fixed;"
        )
        wrapper_style = "width:100%; max-width:100vw; overflow-x:auto;"
        visible_wins = list(range(num_games + 1))
        game_col_style = f"text-align:center; width:{game_col_pct:.4f}%; min-width:38px; max-width:54px; white-space:nowrap;"
        opp_col_style = f"text-align:left; width:{opp_col_pct:.4f}%; min-width:120px; max-width:270px; white-space:nowrap; overflow:hidden;"
        win_col_style = f"text-align:center; width:{win_col_pct:.4f}%; min-width:24px; max-width:40px; white-space:nowrap; overflow:hidden;"
        cell_base_style = win_col_style
        cell_last_style = win_col_style

    def cell_color(p):
        if p <= 0:
            return "background-color:#fff;"
        elif p < 0.25:
            t = p / 0.25
            r = int(224 + (94-224)*t)
            g = int(75 + (160-75)*t)
            b = int(90 + (238-90)*t)
        else:
            t = (p - 0.25) / 0.75
            r = int(94 + (27-94)*t)
            g = int(160 + (60-160)*t)
            b = int(238 + (255-238)*t)
        return f"background-color:rgb({r},{g},{b});"

    table_html = [f'<div style="{wrapper_style}">', f'<table style="{table_style}">', "<thead><tr>"]

    # --- Header row ---
    table_html.append(
        f'<th style="border:1px solid #bbb; padding:{pad}px; background:#eaf1fa; {game_col_style}">Game</th>')
    opp_header_text = "Opponent" if not is_mobile() else "Opp"
    table_html.append(
        f'<th style="border:1px solid #bbb; padding:{pad}px; background:#eaf1fa; {opp_col_style}">{opp_header_text}</th>')

    for w in visible_wins:
        table_html.append(
            f'<th style="border:1px solid #bbb; padding:{pad}px; background:#d4e4f7; {win_col_style}">{w}</th>'
        )
    table_html.append("</tr></thead><tbody>")

    # --- Body rows ---
    for i, row in enumerate(rows):
        table_html.append("<tr>")
        # Game number
        table_html.append(f'<td style="{game_col_style}background:#f8fafb; font-weight:bold; text-align:center;">{row["Game"]}</td>')
        # Opponent logo (mobile: just logo; desktop: logo+name)
        logo_url = opponent_logos[i]
        if is_mobile():
            logo_html = f'<img src="{logo_url}" width="{logo_size}" height="{logo_size}" style="display:block;margin:auto;" alt="">'
        else:
            logo_html = f'<img src="{logo_url}" width="{logo_size}" height="{logo_size}" style="vertical-align:middle;margin-right:3px;"> {row["Opponent"]}'
        table_html.append(f'<td style="{opp_col_style}background:#f8fafb;">{logo_html}</td>')
        game_num = row["Game"]
        for j, w in enumerate(visible_wins):
            is_last = (j == len(visible_wins) - 1)
            style = cell_last_style if is_last else win_col_style
            if w > game_num:
                cell_style = f"{style}background-color:#444; color:#fff; font-family:Arial; text-align:center;"
                cell_text = ""
            else:
                val = row.get(w, 0.0)
                pct = val * 100
                cell_style = (
                    f"{style}{cell_color(val)}"
                    + "color:#222; text-align:center;"
                )
                cell_text = f"{pct:.1f}%"
            table_html.append(f'<td style="{cell_style}">{cell_text}</td>')
        table_html.append("</tr>")
    table_html.append("</tbody></table></div>")

    # --- Prepare chart data (final win distribution) ---
    final_row = rows[-1]
    win_counts = list(range(num_games + 1))
    win_probs = [final_row.get(w, 0.0) for w in win_counts]
    win_probs_pct = [p * 100 for p in win_probs]

    import pandas as pd
    import altair as alt

    df_win_dist = pd.DataFrame({
        "Wins": win_counts,
        "Probability": win_probs_pct
    })
    df_win_dist["Label"] = df_win_dist["Probability"].map(lambda x: f"{x:.1f}%")

    # --- Show table & chart: side by side on desktop, stacked on mobile ---
    if not is_mobile():
        left_col, right_col = st.columns([1, 1])
        with left_col:
            st.markdown("#### Probability Distribution of Wins After Each Game")
            st.markdown("".join(table_html), unsafe_allow_html=True)
        with right_col:
            st.markdown("#### Win Probability Distribution")
            bar = alt.Chart(df_win_dist).mark_bar(
                color="#002060"
            ).encode(
                x=alt.X("Wins:O", axis=alt.Axis(
                    title="Wins",
                    labelAngle=0,
                    labelColor="black",   # <-- Axis tick text
                    titleColor="black"    # <-- Axis label
                )),
                y=alt.Y("Probability:Q", axis=alt.Axis(
                    title="Probability (%)",
                    labelColor="black",
                    titleColor="black"
                )),
                tooltip=[
                    alt.Tooltip("Wins:O", title="Wins"),
                    alt.Tooltip("Probability:Q", format=".1f", title="Probability (%)"),
                ]
            )
            text = bar.mark_text(
                align='center',
                baseline='bottom',
                dy=-2,
                color='black',
                fontSize=10
            ).encode(
                text="Label"
            )
            final_chart = (bar + text).properties(
                width=350,
                height=515,
                title=""
            )
            st.altair_chart(final_chart, use_container_width=True)
    else:
        st.markdown("#### Probability Distribution of Wins After Each Game")
        st.markdown("".join(table_html), unsafe_allow_html=True)
        st.markdown("#### Win Probability Distribution")
        bar = alt.Chart(df_win_dist).mark_bar(
            color="#002060"
        ).encode(
            x=alt.X("Wins:O", axis=alt.Axis(
                title="Wins",
                labelAngle=0,
                labelColor="black",
                titleColor="black"
            )),
            y=alt.Y("Probability:Q", axis=alt.Axis(
                title="Probability (%)",
                labelColor="black",
                titleColor="black"
            )),
            tooltip=[
                alt.Tooltip("Wins:O", title="Wins"),
                alt.Tooltip("Probability:Q", format=".1f", title="Probability (%)"),
            ]
        )
        text = bar.mark_text(
            align='center',
            baseline='bottom',
            dy=-2,
            color='black',
            fontSize=8
        ).encode(
            text="Label"
        )
        final_chart = (bar + text).properties(
            width=340,
            height=240,
            title=""
        )
        st.altair_chart(final_chart, use_container_width=True)

elif tab == "Charts & Graphs":
    st.header("📈 Charts & Graphs")
    import altair as alt

    # --- Load and clean data ---
    df_comp = load_sheet(data_path, "Industry Composite", header=0)
    df_comp.columns = [str(c).strip() for c in df_comp.columns]
    logos_df["Team"] = logos_df["Team"].astype(str)
    df_comp["Team"] = df_comp["Team"].astype(str)

    # --- Clean team names before merge ---
    def clean_team_name(name):
        if pd.isnull(name):
            return ""
        return " ".join(str(name).strip().upper().split())

    logos_df["Team"] = logos_df["Team"].apply(clean_team_name)
    df_comp["Team"] = df_comp["Team"].apply(clean_team_name)

    df_comp = df_comp.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")

    # Warn if missing logos
    missing_logos = df_comp[df_comp["Logo URL"].isna()]["Team"].tolist()
    if missing_logos:
        st.warning(f"Missing logos for: {', '.join(missing_logos[:10])}{'...' if len(missing_logos) > 10 else ''}")

    pr_cols = {
        "JPR": "JPR",
        "Composite": "Composite",
        "SP+": "SP+",
        "FPI": "FPI",
        "KFord": "Kford"
    }
    pr_choices = [k for k, v in pr_cols.items() if v in df_comp.columns]
    selected_rating = st.selectbox(
        "Choose a rating to plot:",
        pr_choices,
        index=0  # JPR as default
    )
    rating_col = pr_cols[selected_rating]

    # --- Include ALL teams (even if missing logo), drop only if missing rating or conference ---
    df = df_comp.dropna(subset=[rating_col, "Conference"]).copy()
    conf_means = df.groupby("Conference", as_index=False)[rating_col].mean()
    conf_means = conf_means.sort_values(rating_col, ascending=False).reset_index(drop=True)
    conf_order = conf_means["Conference"].tolist()
    df["Conference"] = pd.Categorical(df["Conference"], categories=conf_order, ordered=True)

    # Quartile lines
    q1, med, q3 = np.percentile(df[rating_col], [25, 50, 75])
    rule_data = pd.DataFrame({
        rating_col: [q1, med, q3],
        "label": ["Q1", "Med.", "Q3"]
    })

    # Conference trend lines
    line_df = (
        df.groupby("Conference")
        .agg(xmin=(rating_col, "min"), xmax=(rating_col, "max"))
        .reset_index()
    )
    line_df["Conference"] = pd.Categorical(line_df["Conference"], categories=conf_order, ordered=True)

    # Chart display settings
    if is_mobile():
        logo_size = 10
        line_size = 5
        font_size = 9
        left_pad = 0
        point_opacity = 0.96
        height = 340
    else:
        logo_size = 34
        line_size = 14
        font_size = 15
        left_pad = 170
        point_opacity = 1
        height = 95 * len(conf_order) + 120
        width = 1000

    base = alt.Chart(df).encode(
        y=alt.Y("Conference:N", sort=conf_order, title="Conference", axis=alt.Axis(labelFontSize=font_size, titleFontSize=font_size+2)),
        x=alt.X(f"{rating_col}:Q", title=selected_rating, axis=alt.Axis(labelFontSize=font_size, titleFontSize=font_size+2)),
    )

    # Points: logo if available, fallback circle if not
    points_with_logo = base.transform_filter(
        alt.datum["Logo URL"] != None
    ).mark_image(
        width=logo_size,
        height=logo_size,
        opacity=point_opacity
    ).encode(
        url="Logo URL:N",
        tooltip=["Team", rating_col, "Conference"]
    )
    points_no_logo = base.transform_filter(
        alt.datum["Logo URL"] == None
    ).mark_circle(size=logo_size*logo_size, color="#bbbbbb").encode(
        tooltip=["Team", rating_col, "Conference"]
    )

    hlines = alt.Chart(line_df).mark_rule(
        size=line_size, opacity=0.22
    ).encode(
        y=alt.Y("Conference:N", sort=conf_order),
        x="xmin:Q",
        x2="xmax:Q",
        color=alt.Color("Conference:N", scale=alt.Scale(scheme="category10"), legend=None)
    )
    rules = alt.Chart(rule_data).mark_rule(
        strokeDash=[6,4], color="#9067b8", size=2
    ).encode(
        x=f"{rating_col}:Q"
    )
    texts = alt.Chart(rule_data).mark_text(
        dy=-8 if is_mobile() else -16,
        fontWeight="bold",
        fontSize=font_size if is_mobile() else 15,
        color="#9067b8"
    ).encode(
        x=f"{rating_col}:Q",
        y=alt.value(-7 if is_mobile() else -10),
        text="label"
    )

    chart_props = {
        "height": height,
        "title": f"Team {selected_rating} by Conference",
        "padding": {"left": left_pad, "top": 6, "right": 6, "bottom": 6}
    }
    if not is_mobile():
        chart_props["width"] = width

    chart = (rules + texts + hlines + points_with_logo + points_no_logo).properties(**chart_props)

    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")
    st.header("Team Power Ratings Bar Chart")

    # --- Bar chart: repeat cleaning and logo merge ---
    selected_bar_rating = st.selectbox(
        "Choose a rating for bar chart:",
        pr_choices,
        index=0,
        key="bar_chart_rating_select"
    )
    bar_rating_col = pr_cols[selected_bar_rating]

    bar_df = df_comp.dropna(subset=[bar_rating_col, "Conference"]).copy()
    bar_df = bar_df.sort_values(by=bar_rating_col, ascending=False).reset_index(drop=True)
    team_order = bar_df["Team"].tolist()
    bar_df["Team"] = pd.Categorical(bar_df["Team"], categories=team_order, ordered=True)

    conf_list = bar_df["Conference"].unique().tolist()
    palette = alt.Scale(scheme="category10", domain=conf_list)

    if is_mobile():
        bar_logo_size = 14
        bar_font_size = 9
        bar_title_size = 14
        bar_legend = None
        bar_width = None
        bar_size = 10
        bar_height = max(90, bar_size * len(bar_df))
        x_axis = alt.X(f"{bar_rating_col}:Q", title=selected_bar_rating)
        y_axis = alt.Y(
            'Team:N',
            sort=team_order,
            title=None,
            axis=alt.Axis(labels=False, ticks=False)
        )
    else:
        bar_height = 470
        bar_logo_size = 15
        bar_font_size = 11
        bar_width = 900
        bar_title_size = 19
        bar_legend = alt.Legend(title="Conference")
        x_axis = alt.X('Team:N', sort=team_order, title=None, axis=alt.Axis(labels=False, ticks=False))
        y_axis = alt.Y(f"{bar_rating_col}:Q", title=selected_bar_rating)

    bar_props = dict(
        height=bar_height,
        title=alt.TitleParams(
            f"{selected_bar_rating} Ratings by Team",
            fontSize=bar_title_size,
            fontWeight="bold"
        )
    )
    if not is_mobile():
        bar_props["width"] = bar_width

    # Bar chart: all teams, colored by conference, with or without logos
    bar_chart = alt.Chart(bar_df).mark_bar().encode(
        x=x_axis,
        y=y_axis,
        color=alt.Color("Conference:N", scale=palette, legend=bar_legend),
        tooltip=["Team", bar_rating_col, "Conference"]
    ).properties(**bar_props)

    # Logos at bar ends if available, fallback dot otherwise
    logos_on_bar = alt.Chart(bar_df).transform_filter(
        alt.datum["Logo URL"] != None
    ).mark_image(
        width=bar_logo_size,
        height=bar_logo_size
    ).encode(
        x=alt.X(f"{bar_rating_col}:Q") if is_mobile() else alt.X('Team:N', sort=team_order),
        y=alt.Y('Team:N', sort=team_order) if is_mobile() else alt.Y(f"{bar_rating_col}:Q"),
        url="Logo URL:N"
    )
    fallback_bar_dot = alt.Chart(bar_df).transform_filter(
        alt.datum["Logo URL"] == None
    ).mark_circle(size=bar_logo_size*bar_logo_size, color="#bbbbbb").encode(
        x=alt.X(f"{bar_rating_col}:Q") if is_mobile() else alt.X('Team:N', sort=team_order),
        y=alt.Y('Team:N', sort=team_order) if is_mobile() else alt.Y(f"{bar_rating_col}:Q"),
        tooltip=["Team", bar_rating_col, "Conference"]
    )

    final_bar_chart = (bar_chart + logos_on_bar + fallback_bar_dot).configure_axis(
        labelFontSize=bar_font_size,
        titleFontSize=bar_font_size + 2
    )

    st.altair_chart(final_bar_chart, use_container_width=True)


