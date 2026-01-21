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
                    x=leaderboard['Brand'],
                    y=leaderboard['Avg_Rank'],
                    name='Avg Rank (Lower is Better)',
                    mode='lines+markers',
                    marker=dict(color='red', size=10),
                    line=dict(width=3),
                    yaxis='y2'
                ))

                # Layout: Dual Axis with Fixed Range
                fig_combo.update_layout(
                    title='Leaderboard Sorted by Visibility Score (Mentions / Rank)',
                    xaxis=dict(title='Brand'),
                    yaxis=dict(
                        title=dict(text='Mention Count', font=dict(color='#636EFA')),
                        tickfont=dict(color='#636EFA'),
                        range=[0, 10] 
                    ),
                    yaxis2=dict(
                        title=dict(text='Average Rank', font=dict(color='red')),
                        tickfont=dict(color='red'),
                        overlaying='y',
                        side='right',
                        autorange="reversed" 
                    ),
                    legend=dict(x=0.01, y=0.99),
                    barmode='group',
                    height=500
                )
                
                st.plotly_chart(fig_combo, use_container_width=True)
            else:
                st.warning("Not enough data to generate leaderboard yet.")

        col_a, col_b = st.columns(2)

        # --- DATA POINT 2: VECTOR INTELLIGENCE (With KPI) ---
        st.subheader("2. Decision Vector Intelligence")
        
        # Helper to find valid JSON in a column
        def get_first_valid_json(df, col):
            if col not in df.columns:
                return None
            for val in df[col]:
                if isinstance(val, str) and len(val) > 2:
                    return val
            return None

        # Get weights & details
        weights_json = get_first_valid_json(latest_df, 'vector_weights')
        details_json = get_first_valid_json(latest_df, 'vector_details')
        
        if weights_json:
            try:
                weights_map = json.loads(weights_json)
                details = json.loads(details_json) if details_json else {}

                detail_rows = []
                
                # LOOP THROUGH WEIGHTS
                for vec, weight_val in weights_map.items():
                    if weight_val == 0:
                        continue
                    
                    info = details.get(vec)
                    if not info:
                        for d_key in details:
                            if d_key.lower() == vec.lower():
                                info = details[d_key]
                                break
                    info = info or {}

                    detail_rows.append({
                        "Vector": vec,
                        "Weight": f"{weight_val}%",
                        "KPI": info.get("kpi", "N/A"), # NEW COLUMN
                        "Type": info.get("type", "Unknown"),
                        "Sourcing Logic": info.get("source_logic", "N/A")
                    })
                
                if detail_rows:
                    df_view = pd.DataFrame(detail_rows)
                    df_view['_sort'] = df_view['Weight'].apply(lambda x: int(x.strip('%')))
                    df_view = df_view.sort_values(by='_sort', ascending=False).drop(columns=['_sort'])
                    st.dataframe(df_view, hide_index=True, use_container_width=True)
                else:
                    st.caption("No significant vectors found (all weights were 0%).")

            except Exception as e:
                st.error(f"Error parsing Vector Data: {e}")
        else:
            st.info("No vector weights found in the latest data.")

        st.divider()

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

        # --- DATA POINT 4: GAP ANALYSIS (AVERAGE) ---
        with col_c:
            st.subheader("4. Gap from Perfection (Average)")
            if not dff.empty:
                dff['total_distance'] = pd.to_numeric(dff['total_distance'], errors='coerce')
                dff['rank'] = pd.to_numeric(dff['rank'], errors='coerce')
                
                gap_df = dff.groupby('brand').agg({
                    'total_distance': 'mean',
                    'rank': 'mean',
                    'type': 'first'
                }).reset_index()
                
                gap_df.rename(columns={'total_distance': 'Avg_Distance', 'rank': 'Avg_Rank'}, inplace=True)
                gap_df = gap_df.sort_values(by='Avg_Distance')

                fig_gap = px.scatter(gap_df, x='brand', y='Avg_Distance', 
                                     size='Avg_Rank', 
                                     color='type',
                                     title="Average Euclidean Distance (All Time)",
                                     color_discrete_map={"Target": "red", "Competitor": "blue"},
                                     hover_data=['Avg_Rank'])
                
                fig_gap.update_yaxes(range=[10, 0], title="Avg Distance from Perfect 10")
                st.plotly_chart(fig_gap, use_container_width=True)
            else:
                st.info("No data available for gap analysis.")

        # --- DATA POINT 5: STRATEGIC LANDSCAPE ---
        with col_d:
            st.subheader("5. Strategic Landscape")
            if not dff.empty:
                strat_df = dff.groupby('brand').agg({
                    'total_distance': 'mean',
                    'rank': 'mean',
                    'type': 'first',
                    'brand': 'count'
                }).rename(columns={'brand': 'Mentions', 'total_distance': 'Avg_Distance', 'rank': 'Avg_Rank'}).reset_index()

                strat_df['Visibility_Score'] = strat_df['Mentions'] / strat_df['Avg_Rank']

                fig_strat = px.scatter(strat_df, 
                                       x='Visibility_Score', 
                                       y='Avg_Distance', 
                                       color='brand', 
                                       size='Mentions',
                                       title="Visibility (X) vs. Performance (Y)",
                                       labels={'Visibility_Score': 'Share of Visibility (Mentions/Rank)', 'Avg_Distance': 'Euclidean Distance (Lower is Better)'},
                                       hover_data=['Mentions', 'Avg_Rank'])
                
                fig_strat.update_yaxes(range=[10, 0])
                st.plotly_chart(fig_strat, use_container_width=True)
            else:
                st.info("Not enough data for strategic landscape.")

        st.divider()

        # --- DATA POINT 6: SOURCE ATTRIBUTION ---
        st.subheader("6. Source Citations")
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
