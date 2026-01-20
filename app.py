import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from github_utils import load_config, save_config, load_history

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

        # --- DATA POINT 1: SHARE OF VOICE & POSITION ---
        st.subheader("1. Category Leaderboard (Share of Voice)")
        
        # We count how many times each brand appears in the 'Competitor' or 'Target' list
        # Logic: If a brand is in the Top 10, it appears in the rows.
        brand_counts = dff['brand'].value_counts().reset_index()
        brand_counts.columns = ['Brand', 'Mentions']
        
        # Average Rank Calculation
        avg_rank = dff.groupby('brand')['rank'].mean().reset_index()
        leaderboard = pd.merge(brand_counts, avg_rank, on='Brand')
        leaderboard = leaderboard.sort_values(by='Mentions', ascending=False).head(10)
        
        fig_sov = px.bar(leaderboard, x='Mentions', y='Brand', color='rank', 
                         title="Top Brands by Frequency of Mention (All Time)",
                         orientation='h', color_continuous_scale='Bluered_r')
        fig_sov.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_sov, use_container_width=True)

        col_a, col_b = st.columns(2)

        # --- DATA POINT 2: VECTOR WEIGHTS (Rules of the Game) ---
        with col_a:
            st.subheader("2. Decision Vector Weights")
            # Grab the weights from the most recent run (Target row)
            # We look for the row where type='Target' to get the "Master Vectors"
            target_row = latest_df[latest_df['type'] == 'Target'].iloc[0] if not latest_df.empty else None
            
            if target_row is not None and isinstance(target_row['vector_weights'], str):
                weights = json.loads(target_row['vector_weights'])
                w_df = pd.DataFrame(list(weights.items()), columns=['Vector', 'Weight'])
                
                fig_w = px.pie(w_df, values='Weight', names='Vector', 
                               title=f"What Matters in '{selected_case}'?", hole=0.4)
                st.plotly_chart(fig_w, use_container_width=True)
            else:
                st.warning("No vector weights found for this selection.")

        # --- DATA POINT 5: SOURCE ATTRIBUTION ---
        with col_b:
            st.subheader("5. Source Citation Frequency")
            # Aggregate all sources from the filtered view
            all_sources = []
            if 'sources' in dff.columns:
                # Parse every row's source list
                source_lists = dff['sources'].apply(lambda x: json.loads(x) if isinstance(x, str) else [])
                for lst in source_lists:
                    all_sources.extend(lst)
            
            if all_sources:
                source_counts = Counter(all_sources).most_common(10)
                s_df = pd.DataFrame(source_counts, columns=['Source', 'Citations'])
                fig_src = px.bar(s_df, x='Citations', y='Source', orientation='h', 
                                 title="Top Referenced Sources")
                fig_src.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_src, use_container_width=True)
            else:
                st.info("No source data available.")

        st.divider()

        # --- DATA POINT 3 & 4: GAP ANALYSIS & EUCLIDEAN DISTANCE ---
        st.subheader("3 & 4. Competitive Gap Analysis (Distance from Perfect)")
        
        # Scatter plot: X = Brand, Y = Distance
        # We want to distinguish between "Competitors" and "My Brand"
        
        if not latest_df.empty:
            # Sort by rank for cleaner viewing
            latest_df = latest_df.sort_values(by='rank')
            
            fig_gap = px.scatter(latest_df, x='brand', y='total_distance', 
                                 size='rank', color='type',
                                 title=f"Euclidean Distance from Perfection (Lower is Better) - {latest_date}",
                                 color_discrete_map={"Target": "red", "Competitor": "blue"},
                                 hover_data=['rank'])
            
            # Invert Y axis because 0 distance is "Perfect" (Top)
            fig_gap.update_yaxes(autorange="reversed", title="Distance from Perfect 10")
            st.plotly_chart(fig_gap, use_container_width=True)
        
        # --- RAW DATA INSPECTOR ---
        with st.expander("🔍 Inspect Raw Data"):
            st.dataframe(dff)
