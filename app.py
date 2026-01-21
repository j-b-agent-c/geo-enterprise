import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from github_utils import load_config, save_config, load_history, save_history_csv

st.set_page_config(page_title="GEO Command Center", layout="wide")
st.title("🌍 GEO Command Center")

# --- HELPER FUNCTIONS ---
def parse_json_col(df, col_name):
    """Safely parses a column of JSON strings into Python objects."""
    if col_name not in df.columns:
        return []
    return df[col_name].apply(lambda x: json.loads(x) if isinstance(x, str) else {})

# --- TABS ---
tab1, tab2 = st.tabs(["⚙️ Admin Config", "📊 Market Intelligence Dashboard"])

# --- TAB 1: ADMIN (Unchanged) ---
with tab1:
    st.header("Tracker Configuration")
    with st.form("add_target"):
        c1, c2, c3 = st.columns(3)
        brand = c1.text_input("Brand (My Brand)")
        cat = c2.text_input("Category")
        case = c3.text_input("Use Case")
        if st.form_submit_button("Add to Tracker"):
            current = load_config()
            current.append({"brand": brand, "category": cat, "use_case": case})
            save_config(current)
            st.success(f"Added {brand}!")
            st.rerun()

    targets = load_config()
    if targets:
        st.dataframe(pd.DataFrame(targets))
        if st.button("Reset Configuration"):
            save_config([])
            st.rerun()
    
    st.divider()
    st.warning("⚠️ Danger Zone")
    if st.button("🗑️ Clear All Historical Data (history.csv)"):
        save_history_csv(pd.DataFrame())
        st.success("History cleared successfully!")
        st.rerun()

# --- TAB 2: ANALYTICS (The New "Market Sweep" Engine) ---
with tab2:
    df = load_history()
    
    if df.empty:
        st.info("No data yet. Run the 'Daily Audit' GitHub Action to generate your first Market Sweep.")
    else:
        # 0. GLOBAL FILTERS
        st.header("Filters")
        col1, col2 = st.columns(2)
        
        # Get unique categories and use cases from the data
        categories = df['category'].unique() if 'category' in df.columns else []
        selected_cat = col1.selectbox("Select Category", categories)
        
        # Filter data by category first
        cat_df = df[df['category'] == selected_cat].copy()
        
        use_cases = cat_df['use_case'].unique() if 'use_case' in cat_df.columns else []
        selected_case = col2.selectbox("Select Use Case", use_cases)
        
        # Final filtered dataset for this view
        dff = cat_df[cat_df['use_case'] == selected_case].copy()
        
        # Get the latest run date for "Current State" analysis
        latest_date = dff['date'].max()
        latest_df = dff[dff['date'] == latest_date].copy()

        st.divider()

        # --- DATA POINT 1: SHARE OF VOICE & POSITION (COMBO CHART) ---
        st.subheader("1. Category Leaderboard (Weighted by Visibility)")
        
        if not dff.empty:
            # 1. CLEAN DATA
            dff['rank'] = pd.to_numeric(dff['rank'], errors='coerce')
            
            # 2. PREPARE COUNTS
            brand_counts = dff['brand'].value_counts().reset_index()
            brand_counts.columns = ['Brand', 'Mentions'] 
            
            # 3. PREPARE RANKS
            rank_clean = dff.dropna(subset=['rank'])
            avg_rank = rank_clean.groupby('brand')['rank'].mean().reset_index()
            avg_rank.columns = ['Brand', 'Avg_Rank']
            
            # 4. MERGE
            leaderboard = pd.merge(brand_counts, avg_rank, on='Brand')
            
            # CUSTOM METRIC
            leaderboard['Visibility_Score'] = leaderboard['Mentions'] / leaderboard['Avg_Rank']
            leaderboard = leaderboard.sort_values(by='Visibility_Score', ascending=False).head(10)
            
            # 5. BUILD COMBO CHART
            if not leaderboard.empty:
                fig_combo = go.Figure()

                # Trace 1: Bars (Mentions)
                fig_combo.add_trace(go.Bar(
                    x=leaderboard['Brand'],
                    y=leaderboard['Mentions'],
                    name='Mention Count',
                    marker_color='#636EFA',
                    yaxis='y1'
                ))

                # Trace 2: Line (Rank)
                fig_combo.add_trace(go.Scatter(
                    x=leader
