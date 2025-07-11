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

    # ... summary prep code above ...
    left, right = st.columns([1, 1])
    with left:
        # ... summary table rendering ...
        pass  # your summary table code here

    if not is_mobile():
        with right:
            st.markdown("#### Conference Overview Chart Placeholder")
            # (Add chart/plot code here as needed)

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
    df_comp = load_sheet(data_path, "Industry Composite", header=0)
    df_comp.columns = [str(c).strip() for c in df_comp.columns]
    logos_df["Team"] = logos_df["Team"].astype(str).str.strip()
    df_comp["Team"] = df_comp["Team"].astype(str).str.strip()
    df_comp = df_comp.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")

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

    # Sidebar filters
    team_filter = st.sidebar.text_input("Filter by team...", "")
    conf_filter = st.sidebar.text_input("Filter by conference...", "")
    sort_col = st.sidebar.selectbox(
        "Sort by column", display_cols, display_cols.index("Composite Rank") if "Composite Rank" in display_cols else 0
    )
    asc = st.sidebar.checkbox("Ascending order", False)

    df_show = df_comp.copy()
    if team_filter:
        df_show = df_show[df_show["Team"].str.contains(team_filter, case=False, na=False)]
    if conf_filter and "Conference" in df_show.columns:
        df_show = df_show[df_show["Conference"].str.contains(conf_filter, case=False, na=False)]
    df_show = df_show.sort_values(by=sort_col, ascending=asc if not sort_col == "Composite Rank" else True)

    metric_cols = [c for c in all_metrics if c in df_show.columns]
    composite_min, composite_max = df_show["Composite"].min(), df_show["Composite"].max()
    other_metric_cols = [c for c in metric_cols if c != "Composite"]
    col_min = {c: df_show[c].min() for c in other_metric_cols}
    col_max = {c: df_show[c].max() for c in other_metric_cols}

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
                # text color: black for light backgrounds, white for dark
                yiq = ((r*299)+(g*587)+(b*114))/1000
                text_color = "black" if yiq > 140 else "white"
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{text_color}; font-weight:bold;"
                cell = f"<b>{v:.1f}</b>"
            elif c in other_metric_cols and pd.notnull(v):
                mn, mx = col_min[c], col_max[c]
                t = (v - mn) / (mx - mn) if mx > mn else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                # Bold the highest, gray the lowest (only for JPR, SP+, FPI, Kford)
                if c in ["JPR", "SP+", "FPI", "Kford"]:
                    if high_val is not None and abs(v - high_val) < 1e-8:
                        cell = f"<b>{v:.1f}</b>"
                    elif low_val is not None and abs(v - low_val) < 1e-8:
                        td += " color:#bbb;"
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

    if logo_url:
        conference = team_row["Conference"] if "Conference" in team_row else ""
        conf_logo_url = None
        if conference in logos_df["Team"].values:
            conf_logo_url = logos_df.loc[logos_df["Team"] == conference, "Logo URL"].values[0]
        st.markdown(
            f'''
            <div style="display: flex; align-items: center; gap:18px; margin-top:8px; margin-bottom:10px;">
                <img src="{logo_url}" width="48" style="display:inline-block;"/>
                {f"<img src='{conf_logo_url}' width='48' style='display:inline-block;'/>" if conf_logo_url else ""}
            </div>
            ''',
            unsafe_allow_html=True
        )

    # ---- Team Schedule Table ----
    team_col = [col for col in df_schedule.columns if "Team" in col][0]
    sched = df_schedule[df_schedule[team_col] == selected_team].copy()

    # --- Calculate Win Distribution Table (paste here) ---
    import numpy as np

    win_probs = sched["Win Probability"].values if "Win Probability" in sched.columns else sched["Win Prob"].values
    opponents = sched["Opponent"].tolist()
    num_games = len(win_probs)

    dp = np.zeros((num_games + 1, num_games + 1))
    dp[0, 0] = 1.0

    for g in range(1, num_games + 1):
        p = win_probs[g-1]
        for w in range(g+1):
            win_part = dp[g-1, w-1] * p if w > 0 else 0
            lose_part = dp[g-1, w] * (1 - p)
            dp[g, w] = win_part + lose_part

    rows = []
    for g in range(1, num_games + 1):
        row = {
            "Game": g,
            "Opponent": opponents[g-1]
        }
        for w in range(num_games + 1):
            row[w] = dp[g, w]
        rows.append(row)

    # --- Responsive Settings ---
    n_cols = 2 + num_games + 1  # Game + Opponent + win columns
    col_pct = 100 / n_cols
    if is_mobile():
        font_size = 7
        pad = 0.5
        min_opp_width = 18
        min_num_width = 9
        table_style = (
            f"font-size:{font_size}px; width:100vw; max-width:100vw; table-layout:fixed; border-collapse:collapse;"
        )
        wrapper_style = "max-width:100vw; overflow-x:hidden; margin:0;"
        visible_wins = list(range(num_games + 1))
        show_extra = False
        logo_size = 18  # px
    else:
        font_size = 13
        pad = 4
        min_opp_width = 110
        min_num_width = 38
        table_style = f"font-size:{font_size}px; min-width:800px;"
        wrapper_style = "overflow-x:auto; max-width:100vw;"
        visible_wins = list(range(num_games + 1))
        show_extra = False
        logo_size = 34

    # --- Blue-Heavy Gradient, Impossible Cells Dark Grey ---
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

    # --- Get opponent logos for each game ---
    # Assume you have a DataFrame `logos_df` with "Team" and "Logo URL" columns
    opponent_logos = []
    for opp in opponents:
        logo_url = ""
        try:
            # Find the logo for this opponent, fallback to blank
            logo_url = logos_df.loc[logos_df["Team"].str.lower() == str(opp).strip().lower(), "Logo URL"].values[0]
        except Exception:
            logo_url = ""
        opponent_logos.append(logo_url)

    # --- Build Table HTML ---
    table_html = [
        f'<div style="{wrapper_style}">',
        f'<table style="{table_style}">',
        "<thead><tr>"
    ]
    table_html.append(
        f'<th style="border:1px solid #bbb; padding:{pad}px {pad+1}px; background:#eaf1fa; text-align:center; width:{col_pct:.2f}vw;">Game</th>')
    table_html.append(
        f'<th style="border:1px solid #bbb; padding:{pad}px {pad+1}px; background:#eaf1fa; text-align:center; width:{col_pct:.2f}vw;">Opp</th>')
    for w in visible_wins:
        table_html.append(
            f'<th style="border:1px solid #bbb; padding:{pad}px {pad+1}px; background:#d4e4f7; text-align:center; width:{col_pct:.2f}vw;">{w}</th>'
        )
    table_html.append("</tr></thead><tbody>")

    for i, row in enumerate(rows):
        table_html.append("<tr>")
        # Game number
        table_html.append(
            f'<td style="border:1px solid #bbb; padding:{pad}px {pad+1}px; background:#f8fafb; text-align:center; font-weight:bold; width:{col_pct:.2f}vw;">{row["Game"]}</td>')
        # Opponent logo (mobile: small and centered)
        logo_html = ""
        logo_url = opponent_logos[i]
        if is_mobile() and logo_url:
            logo_html = f'<img src="{logo_url}" width="{logo_size}" height="{logo_size}" style="display:block;margin:auto;" alt="">'
        elif logo_url:
            logo_html = f'<img src="{logo_url}" width="{logo_size}" height="{logo_size}" style="vertical-align:middle;margin-right:5px;"> {row["Opponent"]}'
        else:
            logo_html = row["Opponent"]
        table_html.append(
            f'<td style="border:1px solid #bbb; padding:{pad}px {pad+1}px; background:#f8fafb; text-align:center; width:{col_pct:.2f}vw;">{logo_html}</td>'
        )

        game_num = row["Game"]
        for w in visible_wins:
            if w > game_num:
                cell_style = (
                    f"border:1px solid #bbb; padding:{pad}px {pad+1}px; text-align:center; "
                    f"background-color:#444; color:#fff; font-family:Arial; width:{col_pct:.2f}vw;"
                )
                cell_text = ""
            else:
                val = row.get(w, 0.0)
                pct = val * 100
                cell_style = (
                    f"border:1px solid #bbb; padding:{pad}px {pad+1}px; text-align:center; font-family:Arial; width:{col_pct:.2f}vw;"
                    + cell_color(val)
                    + ("color:#333; font-weight:bold;" if pct > 50 else "color:#222;")
                )
                cell_text = f"{pct:.1f}%"
            table_html.append(f'<td style="{cell_style}">{cell_text}</td>')
        table_html.append("</tr>")
    table_html.append("</tbody></table></div>")

    st.markdown("#### Probability Distribution of Wins After Each Game")
    st.markdown("".join(table_html), unsafe_allow_html=True)

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
                    style += "min-width:30vw; max-width:38vw; word-break:break-word; font-size:12px;"
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


elif tab == "Charts & Graphs":

    st.header("📈 Charts & Graphs")
    import altair as alt

    # --- Load Industry Composite if not already loaded ---
    df_comp = load_sheet(data_path, "Industry Composite", header=0)
    df_comp.columns = [str(c).strip() for c in df_comp.columns]
    logos_df["Team"] = logos_df["Team"].astype(str).str.strip()
    df_comp["Team"] = df_comp["Team"].astype(str).str.strip()
    df_comp = df_comp.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")

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

    # Prepare data
    df = df_comp.dropna(subset=[rating_col, "Conference", "Logo URL"]).copy()
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

    # Data for horizontal conference "trendlines" (min to max for each conf)
    line_df = (
        df.groupby("Conference")
        .agg(xmin=(rating_col, "min"), xmax=(rating_col, "max"))
        .reset_index()
    )
    line_df["Conference"] = pd.Categorical(line_df["Conference"], categories=conf_order, ordered=True)

    # Set chart display variables based on device
    if is_mobile():
        # --- MOBILE VERSION: Tiny logos, minimal padding, perfectly square ---
        logo_size = 10
        line_size = 5
        font_size = 9
        left_pad = 0
        point_opacity = 0.96
        # Hardcode the height for square shape (Altair/Streamlit auto-fills width)
        height = 340
    else:
        logo_size = 34
        line_size = 14
        font_size = 15
        left_pad = 170
        point_opacity = 1
        height = 95*len(conf_order) + 120
        width = 1000


    base = alt.Chart(df).encode(
        y=alt.Y("Conference:N", sort=conf_order, title="Conference", axis=alt.Axis(labelFontSize=font_size, titleFontSize=font_size+2)),
        x=alt.X(f"{rating_col}:Q", title=selected_rating, axis=alt.Axis(labelFontSize=font_size, titleFontSize=font_size+2)),
    )

    points = base.mark_image(
        width=logo_size,
        height=logo_size,
        opacity=point_opacity
    ).encode(
        url="Logo URL:N",
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

    # Properties dict for mobile/desktop
    chart_props = {
        "height": height,
        "title": f"Team {selected_rating} by Conference",
        "padding": {"left": left_pad, "top": 6, "right": 6, "bottom": 6}
    }
    if not is_mobile():
        chart_props["width"] = width  # Only set width on desktop

    chart = (rules + texts + hlines + points).properties(**chart_props)

    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")
    st.header("Team Power Ratings Bar Chart")

# ---- Independent rating filter for this chart ----
    selected_bar_rating = st.selectbox(
        "Choose a rating for bar chart:",
        pr_choices,
        index=0,  # Default to JPR
        key="bar_chart_rating_select"
    )
    bar_rating_col = pr_cols[selected_bar_rating]

# Data prep for bar chart
    bar_df = df_comp.dropna(subset=[bar_rating_col, "Conference", "Logo URL"]).copy()
# Order teams by selected rating (descending: highest first)
    bar_df = bar_df.sort_values(by=bar_rating_col, ascending=False).reset_index(drop=True)
    team_order = bar_df["Team"].tolist()
    bar_df["Team"] = pd.Categorical(bar_df["Team"], categories=team_order, ordered=True)

# Conference color mapping
    conf_list = bar_df["Conference"].unique().tolist()
    palette = alt.Scale(scheme="category10", domain=conf_list)

    if is_mobile():
    # --- MOBILE: Horizontal bar chart, minimal gap, skinny bars ---
        bar_logo_size = 14
        bar_font_size = 9
        bar_title_size = 14
        bar_legend = None
        bar_width = None
        bar_size = 10  # Skinny bars!
        bar_height = max(90, bar_size * len(bar_df))  # bar_size per team; reduces gaps
        x_axis = alt.X(f"{bar_rating_col}:Q", title=selected_bar_rating)
        y_axis = alt.Y(
            'Team:N',
            sort=team_order,
            title=None,
            axis=alt.Axis(labels=False, ticks=False)
        )

    else:
    # --- DESKTOP: Vertical bar chart, legend on ---
        bar_height = 470
        bar_logo_size = 15
        bar_font_size = 11
        bar_width = 900
        bar_title_size = 19
        bar_legend = alt.Legend(title="Conference")
        x_axis = alt.X('Team:N', sort=team_order, title=None, axis=alt.Axis(labels=False, ticks=False))
        y_axis = alt.Y(f"{bar_rating_col}:Q", title=selected_bar_rating)

# Properties dict for width only on desktop
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

    if is_mobile():
        bar_chart = alt.Chart(bar_df).mark_bar(
            color="gray"
        # No border on mobile: do NOT include stroke or strokeWidth
        ).encode(
            x=x_axis,
            y=y_axis,
            color=alt.Color("Conference:N", scale=palette, legend=bar_legend),
            tooltip=["Team", bar_rating_col, "Conference"]
        ).properties(**bar_props)
    else:
        bar_chart = alt.Chart(bar_df).mark_bar(
            color="gray",
            stroke="black",
            strokeWidth=1.2
        ).encode(
            x=x_axis,
            y=y_axis,
            color=alt.Color("Conference:N", scale=palette, legend=bar_legend),
            tooltip=["Team", bar_rating_col, "Conference"]
        ).properties(**bar_props)


# Logos at the end of the bar
    if is_mobile():
    # Mobile: logos on x at end of horizontal bar
        logo_points = alt.Chart(bar_df).mark_image(
            width=bar_logo_size,
            height=bar_logo_size
        ).encode(
            x=alt.X(f"{bar_rating_col}:Q"),
            y=alt.Y('Team:N', sort=team_order),
            url="Logo URL:N"
        )
    else:
    # Desktop: logos on y at end of vertical bar
        logo_points = alt.Chart(bar_df).mark_image(
            width=bar_logo_size,
            height=bar_logo_size
        ).encode(
            x=alt.X('Team:N', sort=team_order),
            y=alt.Y(f"{bar_rating_col}:Q"),
            url="Logo URL:N"
        )

    final_bar_chart = (bar_chart + logo_points).configure_axis(
        labelFontSize=bar_font_size,
        titleFontSize=bar_font_size + 2
    )
    
    st.altair_chart(final_bar_chart, use_container_width=True)
