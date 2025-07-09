import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import streamlit.components.v1 as components

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

# Normalize team names and prepare logos
logos_df["Team"] = logos_df["Team"].str.strip()
df_expected["Team"] = df_expected["Team"].str.strip()
if "Image URL" in logos_df.columns:
    logos_df.rename(columns={"Image URL": "Logo URL"}, inplace=True)
team_logos = logos_df[logos_df["Team"].isin(df_expected["Team"])][["Team","Logo URL"]]
df_expected = df_expected.merge(team_logos, on="Team", how="left")

# --- Streamlit Config ---
FORCE_MOBILE = st.sidebar.checkbox("Mobile View", False)
def is_mobile(): return FORCE_MOBILE

# Set page config early
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed" if is_mobile() else "expanded"
)

st.title("🎯 College Football 2025 Pre-Season Preview")

# Inject CSS to freeze table headers
st.markdown("""
<style>
  thead th {
    position: -webkit-sticky;
    position: sticky;
    top: 0;
    background-color: #002060;
    color: white;
    z-index: 2;
  }
</style>
""", unsafe_allow_html=True)

# --- Data Cleaning & Renaming ---
df_expected["Conference"] = (
    df_expected["Conference"].astype(str)
    .str.strip()
    .str.replace("-", "", regex=False)
    .str.upper()
)
empty_cols = [c for c in df_expected.columns if str(c).strip() == ""]
df_expected.drop(columns=empty_cols, inplace=True, errors='ignore')
df_expected.drop(columns=["Column1","Column3"], inplace=True, errors='ignore')
rename_map = { ... }  # same as before
df_expected.rename(columns=rename_map, inplace=True)
if "Preseason Rank" not in df_expected.columns:
    df_expected.insert(0, "Preseason Rank", list(range(1, len(df_expected)+1)))
# format & rounding as before...

# --- Sidebar & Tabs ---
tab = st.sidebar.radio("Navigation", ["Rankings","Conference Overviews","Team Dashboards","Charts & Graphs"])

if tab == "Rankings":
    st.header("📋 Rankings")
    # filter/sort inputs...
    df = df_expected.copy()
    # apply filters/sorting...

    # define columns and headers for mobile/desktop as before...
    # build HTML table with inline CSS for cells, relying on injected CSS for headers
    html = []
    html.append('<div style="max-width:100%; overflow-x:auto;">')
    html.append('<table style="width:100%; border-collapse:collapse; table-layout:fixed;">')
    html.append('<thead><tr>')
    for col in cols_rank:
        th_style = (
            'border:1px solid #ddd; padding:8px; text-align:center; ' +
            ('white-space:nowrap; min-width:48px; ' if col=="Team" and is_mobile() else '')
        )
        html.append(f"<th style='{th_style}'>{display_header_map[col]}</th>")
    html.append('</tr></thead><tbody>')
    for _,row in df.iterrows():
        html.append('<tr>')
        for col in cols_rank:
            # cell rendering as before...
            html.append(f"<td style='{td}'>{cell}</td>")
        html.append('</tr>')
    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)

elif tab == "Conference Overviews":
    st.header("🏟️ Conference Overviews")
    # Data prep as before...
    left,right = st.columns(2)
    with left:
        st.markdown('<div style="overflow-x:auto;">', unsafe_allow_html=True)
        st.markdown('<table style="width:100%; border-collapse:collapse;">', unsafe_allow_html=True)
        # headers rely on CSS injection now
        header_html = '<thead><tr>' + ''.join(
            f"<th style='border:1px solid #ddd; padding:8px; text-align:center;'>{c}</th>" for c in cols_sum
        ) + '</tr></thead>'
        st.markdown(header_html, unsafe_allow_html=True)
        body_html = '<tbody>' + ''.join(... ) + '</tbody></table></div>'
        st.markdown(body_html, unsafe_allow_html=True)
    with right:
        st.markdown("#### Conference Overview Chart Placeholder")

# Team Dashboards & Charts tabs...
