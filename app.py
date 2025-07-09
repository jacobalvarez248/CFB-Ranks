import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt

# Helper to load Excel sheets via pandas
from pandas import DataFrame

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
    except Exception:
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

# Clean and merge logo URLs
df_expected['Team'] = df_expected['Team'].str.strip()
logos_df['Team'] = logos_df['Team'].str.strip()
if 'Image URL' in logos_df.columns:
    logos_df.rename(columns={'Image URL': 'Logo URL'}, inplace=True)
team_logos = logos_df[['Team','Logo URL']]
df_expected = df_expected.merge(team_logos, on='Team', how='left')

# --- Streamlit Config ---
# Toggle mobile view
mobile_toggle = st.sidebar.checkbox("Mobile View", False)

# Set page config early
st.set_page_config(
    page_title="CFB 2025 Preview",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed" if mobile_toggle else "expanded"
)

st.title("🎯 College Football 2025 Pre-Season Preview")

# --- Data Cleaning & Renaming ---
# Normalize conference names
if 'Conference' in df_expected.columns:
    df_expected['Conference'] = (
        df_expected['Conference'].astype(str)
        .str.strip()
        .str.replace('-', '', regex=False)
        .str.upper()
    )
# Remove blank columns
df_expected = df_expected.loc[:, df_expected.columns.str.strip() != '']
# Rename columns
rename_map = {
    'Column18': 'Power Rating',
    'Projected Overall Record': 'Projected Overall Wins',
    'Column2': 'Projected Overall Losses',
    'Projected Conference Record': 'Projected Conference Wins',
    'Column4': 'Projected Conference Losses',
    'Pick': 'OVER/UNDER Pick',
    'Column17': 'Schedule Difficulty Rank',
    'xWins for Playoff Team': 'Schedule Difficulty Rating',
    'Winless Probability': 'Average Game Quality',
}
df_expected.rename(columns=rename_map, inplace=True)
# Add Preseason Rank if missing
if 'Preseason Rank' not in df_expected.columns:
    df_expected.insert(0, 'Preseason Rank', range(1, len(df_expected)+1))
# Format percentages and round numbers
for col in ['Undefeated Probability']:
    if col in df_expected:
        df_expected[col] = df_expected[col].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else x)
# Round numeric columns excluding rank columns
rank_cols = ['Preseason Rank', 'Schedule Difficulty Rank']
for col in df_expected.select_dtypes(include='number').columns:
    if col not in rank_cols:
        df_expected[col] = df_expected[col].round(1)

# --- Sidebar Filters & Navigation ---
tab = st.sidebar.radio(
    "Navigation",
    ['Rankings','Conference Overviews','Team Dashboards','Charts & Graphs']
)

# Common filters for Rankings
team_search = st.sidebar.text_input("Search Team", '')
conf_search = st.sidebar.text_input("Filter Conference", '')
sort_col = st.sidebar.selectbox("Sort By", df_expected.columns, index=0)
asc = st.sidebar.checkbox("Ascending", True)

# ------ Rankings Tab ------
if tab == 'Rankings':
    st.header('📋 Rankings')
    df = df_expected.copy()
    if team_search:
        df = df[df['Team'].str.contains(team_search, case=False, na=False)]
    if conf_search and 'Conference' in df.columns:
        df = df[df['Conference'].str.contains(conf_search, case=False, na=False)]
    try:
        df = df.sort_values(sort_col, ascending=asc)
    except Exception:
        df = df.sort_values(sort_col.astype(str), ascending=asc)
    # Display table with sticky headers
    st.dataframe(df, use_container_width=True, height=600)

# ------ Conference Overviews Tab ------
elif tab == 'Conference Overviews':
    st.header('🏟️ Conference Overviews')
    # Summary metrics
    summary = (
        df_expected.groupby('Conference')
        .agg(**{
            '# Teams': ('Preseason Rank','count'),
            'Avg Power Rating': ('Power Rating','mean'),
            'Avg Game Quality': ('Average Game Quality','mean'),
            'Avg Schedule Difficulty': ('Schedule Difficulty Rating','mean')
        })
        .round(1)
        .reset_index()
    )
    st.dataframe(summary, use_container_width=True, height=600)

# ------ Team Dashboards Tab ------
elif tab == 'Team Dashboards':
    st.header('🏈 Team Dashboards')
    st.info('Team dashboards to be implemented')

# ------ Charts & Graphs Tab ------
elif tab == 'Charts & Graphs':
    st.header('📊 Charts & Graphs')
    st.info('Charts & Graphs to be implemented')
