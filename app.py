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

        # --- DATA POINT 1: SHARE OF VOICE & POSITION (COMBO CHART) ---
        st.subheader("1. Category Leaderboard (Mentions vs. Rank)")
        
        if not dff.empty:
            # 1. CLEAN DATA: Ensure 'rank' is numeric
            dff['rank'] = pd.to_numeric(dff['rank'], errors='coerce')
            
            # 2. PREPARE COUNTS
            brand_counts = dff['brand'].value_counts().reset_index()
            # Explicitly rename columns to handle any Pandas version differences
            brand_counts.columns = ['Brand', 'Mentions'] 
            
            # 3. PREPARE RANKS (Drop missing ranks before averaging)
            rank_clean = dff.dropna(subset=['rank'])
            avg_rank = rank_clean.groupby('brand')['rank'].mean().reset_index()
            avg_rank.columns = ['Brand', 'Avg_Rank']
            
            # 4. MERGE (Inner join ensures we only chart brands that have both data points)
            leaderboard = pd.merge(brand_counts, avg_rank, on='Brand')
            leaderboard = leaderboard.sort_values(by='Mentions', ascending=False).head(10)
            
            # 5. BUILD COMBO CHART
            if not leaderboard.empty:
                fig_combo = go.Figure()

                # Trace 1: Bars for Mentions (Left Axis)
                fig_combo.add_trace(go.Bar(
                    x=leaderboard['Brand'],
                    y=leaderboard['Mentions'],
                    name='Mention Count',
                    marker_color='#636EFA',
                    yaxis='y1'
                ))

                # Trace 2: Line/Markers for Avg Rank (Right Axis)
                fig_combo.add_trace(go.Scatter(
                    x=leaderboard['Brand'],
                    y=leaderboard['Avg_Rank'],
                    name='Avg Rank (Lower is Better)',
                    mode='lines+markers',
                    marker=dict(color='red', size=10),
                    line=dict(width=3),
                    yaxis='y2'
                ))

                # Layout: Dual Axis Setup
                fig_combo.update_layout(
                    title='Share of Voice (Bars) vs. Average Rank (Line)',
                    xaxis=dict(title='Brand'),
                    yaxis=dict(
                        title='Mention Count',
                        titlefont=dict(color='#636EFA'),
                        tickfont=dict(color='#636EFA')
                    ),
                    yaxis2=dict(
                        title='Average Rank',
                        titlefont=dict(color='red'),
                        tickfont=dict(color='red'),
                        overlaying='y',
                        side='right',
                        autorange="reversed" # Invert so Rank 1 is at the top
                    ),
                    legend=dict(x=0.01, y=0.99),
                    barmode='group',
                    height=500
                )
                
                st.plotly_chart(fig_combo, use_container_width=True)
            else:
                st.warning("Not enough data to generate leaderboard yet.")

        col_a, col_b = st.columns(2)

        # --- DATA POINT 2: VECTOR WEIGHTS ---
        with col_a:
            st.subheader("2. Decision Vector Weights")
            target_row = latest_df[latest_df['type'] == 'Target'].iloc[0] if not latest_df.empty and 'type' in latest_df.columns and (latest_df['type'] == 'Target').any() else None
            
            if target_row is not None and isinstance(target_row['vector_weights'], str):
                try:
                    weights = json.loads(target_row['vector_weights'])
                    w_df = pd.DataFrame(list(weights.items()), columns=['Vector', 'Weight'])
                    fig_w = px.pie(w_df, values='Weight', names='Vector', 
                                   title=f"What Matters in '{selected_case}'?", hole=0.4)
                    st.plotly_chart(fig_w, use_container_width=True)
                except:
                    st.warning("Could not parse vector weights.")
            else:
                st.info("No vector weights found for this selection.")

        # --- DATA POINT 3: COMPETITIVE SCORECARD ---
        st.subheader("3. Detailed Competitive Scorecard")
        if not latest_df.empty and 'vector_scores' in latest_df.columns:
            score_data = []
            for idx, row in latest_df.iterrows():
                try:
                    scores = json.loads(row['vector_scores'])
                    scores['Brand'] = row['brand']
                    score_data.append(scores)
                except:
                    continue
            
            if score_data:
                scores_df = pd.DataFrame(score_data)
                scores_df = scores_df.set_index('Brand')
                fig_hm = px.imshow(scores_df, text_auto=True, aspect="auto",
                                   color_continuous_scale='RdBu', 
                                   title=f"Head-to-Head: Brand Scores per Vector ({latest_date})")
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("No detailed score data available.")

        st.divider()

        col_c, col_d = st.columns(2)

        # --- DATA POINT 4: GAP ANALYSIS ---
        with col_c:
            st.subheader("4. Gap from Perfection")
            if not latest_df.empty:
                # Ensure rank is numeric for sorting/sizing
                latest_df['rank'] = pd.to_numeric(latest_df['rank'], errors='coerce')
                latest_df = latest_df.sort_values(by='rank')
                
                fig_gap = px.scatter(latest_df, x='brand', y='total_distance', 
                                     size='rank', color='type',
                                     title="Euclidean Distance (Lower is Better)",
                                     color_discrete_map={"Target": "red", "Competitor": "blue"},
                                     hover_data=['rank'])
                fig_gap.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_gap, use_container_width=True)

        # --- DATA POINT 5: SOURCE ATTRIBUTION ---
        with col_d:
            st.subheader("5. Source Citations")
            all_sources = []
            if 'sources' in dff.columns:
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

        with st.expander("🔍 Inspect Raw Data"):
            st.dataframe(dff)
