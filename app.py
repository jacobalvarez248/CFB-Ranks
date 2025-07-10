import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import io

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
        "Average Game Quality": "Avg. Game QTY",
        "Schedule Difficulty Rating": "Sched. Diff."
    }
    mobile_cols = list(mobile_header_map.keys())
    desktop_cols = [
        "Projected Finish", "Team", "Power Rating", "Projected Overall Wins",
        "Projected Conference Wins", "Projected Conference Losses",
        "Average Game Quality", "Schedule Difficulty Rank", "Schedule Difficulty Rating"
    ]
    pr_min, pr_max = standings["Power Rating"].min(), standings["Power Rating"].max()
    agq_min, agq_max = standings["Average Game Quality"].min(), standings["Average Game Quality"].max()
    sdr_min, sdr_max = standings["Schedule Difficulty Rating"].min(), standings["Schedule Difficulty Rating"].max()

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
        "Projected Overall Losses", "Projected Conference Losses", "Average Game Quality",
        "Schedule Difficulty Rank", "Schedule Difficulty Rating"
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
elif tab == "Industry Composite Ranking":
    st.header("📊 Industry Composite Ranking")
    df_comp = load_sheet(data_path, "Industry Composite", header=0)
    df_comp.columns = [str(c).strip() for c in df_comp.columns]
    logos_df["Team"] = logos_df["Team"].astype(str).str.strip()
    df_comp["Team"] = df_comp["Team"].astype(str).str.strip()
    df_comp = df_comp.merge(logos_df[["Team", "Logo URL"]], on="Team", how="left")

    # Columns to display
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

    format_cols = [c for c in all_metrics if c in df_show.columns]
    col_min = {c: df_show[c].min() for c in format_cols}
    col_max = {c: df_show[c].max() for c in format_cols}

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
    compact_cols = ["Composite Rank", "Conference", "Composite","JPR","SP+","FPI","Kford"]
    for disp_col, c in zip(display_headers, display_cols):
        th = (
            'border:1px solid #ddd; padding:8px; text-align:center; background-color:#002060; color:white; '
            'position:sticky; top:0; z-index:2;'
        )
        if c == "Team":
            th += " white-space:nowrap; min-width:120px; max-width:260px;"
        elif not is_mobile() and c in compact_cols:
            th += " min-width:60px; max-width:72px; white-space:normal; font-size:13px; line-height:1.2;"
        else:
            th += " white-space:nowrap;"
        th += header_font
        html.append(f"<th style='{th}'>{disp_col}</th>")
    html.append("</tr></thead><tbody>")

    for _, row in df_show.iterrows():
        html.append("<tr>")
        for c in display_cols:
            v = row[c]
            td = 'border:1px solid #ddd; padding:8px; text-align:center;'
            td += cell_font
            cell = v
            if c == "Team":
                logo = row.get("Logo URL")
                team_name = v
                if pd.notnull(logo) and isinstance(logo, str) and logo.startswith("http"):
                    # Always side-by-side (both desktop and mobile)
                    cell = (
                        f'<div style="display:flex;align-items:center;">'
                        f'<img src="{logo}" width="24" style="margin-right:8px;"/>{team_name}</div>'
                    )
                else:
                    cell = team_name
            elif c == "Composite Rank":
                cell = f"{int(v)}"
            elif c in format_cols and pd.notnull(v):
                mn, mx = col_min[c], col_max[c]
                t = (v - mn) / (mx - mn) if mx > mn else 0
                r, g, b = [int(255 + (x - 255) * t) for x in (0, 32, 96)]
                td += f" background-color:#{r:02x}{g:02x}{b:02x}; color:{'black' if t<0.5 else 'white'};"
                val_str = f"{v:.1f}"
                if c == "Composite":
                    cell = f"<b>{val_str}</b>"
                else:
                    cell = val_str
            else:
                cell = v
            html.append(f"<td style='{td}'>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)



