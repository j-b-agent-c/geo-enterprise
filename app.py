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
    if col_name not in df.columns: return []
    return df[col_name].apply(lambda x: json.loads(x) if isinstance(x, str) else {})

# --- TABS ---
tab1, tab2 = st.tabs(["⚙️ Admin Config", "📊 Market Intelligence Dashboard"])

# --- TAB 1: ADMIN ---
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
    if st.button("🗑️ Clear All Historical Data"):
        save_history_csv(pd.DataFrame())
        st.success("History cleared!")
        st.rerun()

# --- TAB 2: ANALYTICS ---
with tab2:
    df = load_history()
    
    if df.empty:
        st.info("No data yet. Run the 'Daily Audit' GitHub Action.")
    else:
        st.header("Filters")
        col1, col2 = st.columns(2)
        categories = df['category'].unique() if 'category' in df.columns else []
        selected_cat = col1.selectbox("Select Category", categories)
        cat_df = df[df['category'] == selected_cat].copy()
        
        use_cases = cat_df['use_case'].unique() if 'use_case' in cat_df.columns else []
        selected_case = col2.selectbox("Select Use Case", use_cases)
        dff = cat_df[cat_df['use_case'] == selected_case].copy()
        
        latest_date = dff['date'].max()
        latest_df = dff[dff['date'] == latest_date].copy()

        st.divider()

        # 1. LEADERBOARD
        st.subheader("1. Category Leaderboard (Weighted by Visibility)")
        if not dff.empty:
            dff['rank'] = pd.to_numeric(dff['rank'], errors='coerce')
            brand_counts = dff['brand'].value_counts().reset_index()
            brand_counts.columns = ['Brand', 'Mentions'] 
            rank_clean = dff.dropna(subset=['rank'])
            avg_rank = rank_clean.groupby('brand')['rank'].mean().reset_index()
            avg_rank.columns = ['Brand', 'Avg_Rank']
            leaderboard = pd.merge(brand_counts, avg_rank, on='Brand')
            leaderboard['Visibility_Score'] = leaderboard['Mentions'] / leaderboard['Avg_Rank']
            leaderboard = leaderboard.sort_values(by='Visibility_Score', ascending=False).head(10)
            
            fig_combo = go.Figure()
            fig_combo.add_trace(go.Bar(x=leaderboard['Brand'], y=leaderboard['Mentions'], name='Mentions', marker_color='#636EFA', yaxis='y1'))
            fig_combo.add_trace(go.Scatter(x=leaderboard['Brand'], y=leaderboard['Avg_Rank'], name='Avg Rank', mode='lines+markers', marker=dict(color='red'), yaxis='y2'))
            fig_combo.update_layout(
                title='Visibility Leaderboard', 
                yaxis=dict(title='Mentions'), 
                yaxis2=dict(title='Avg Rank', overlaying='y', side='right', autorange="reversed"),
                legend=dict(x=0.01, y=0.99), height=500
            )
            st.plotly_chart(fig_combo, use_container_width=True)

        col_a, col_b = st.columns(2)

        # 2. VECTOR INTELLIGENCE
        st.subheader("2. Decision Vector Intelligence")
        weights_json = None
        details_json = None
        for val in latest_df['vector_weights']:
             if isinstance(val, str) and len(val) > 2: weights_json = val; break
        for val in latest_df['vector_details']:
             if isinstance(val, str) and len(val) > 2: details_json = val; break
        
        if weights_json:
            try:
                weights_map = json.loads(weights_json)
                details = json.loads(details_json) if details_json else {}
                detail_rows = []
                for vec, weight_val in weights_map.items():
                    if weight_val == 0: continue
                    info = details.get(vec)
                    if not info:
                        for k in details:
                            if k.lower() == vec.lower(): info = details[k]; break
                    info = info or {}
                    detail_rows.append({
                        "Vector": vec, "Weight": f"{weight_val}%", 
                        "KPI": info.get("kpi", "N/A"), "Type": info.get("type", "Unknown"), 
                        "Sourcing Logic": info.get("source_logic", "N/A")
                    })
                df_view = pd.DataFrame(detail_rows)
                df_view['_sort'] = df_view['Weight'].apply(lambda x: int(x.strip('%')))
                df_view = df_view.sort_values(by='_sort', ascending=False).drop(columns=['_sort'])
                st.dataframe(df_view, hide_index=True, use_container_width=True)
            except Exception as e: st.error(f"Error: {e}")
        else: st.info("No vector data.")

        st.divider()

        # 3. COMPETITIVE SCORECARD & EVIDENCE INSPECTOR
        st.subheader("3. Detailed Competitive Scorecard")
        if not latest_df.empty and 'vector_scores' in latest_df.columns:
            score_data = []
            citations_map = {}
            for idx, row in latest_df.iterrows():
                try:
                    scores = json.loads(row['vector_scores'])
                    scores['Brand'] = row['brand']
                    score_data.append(scores)
                    if 'vector_citations' in row:
                        val = row['vector_citations']
                        if isinstance(val, str) and len(val) > 2:
                             citations_map[row['brand']] = json.loads(val)
                except: continue
            
            if score_data:
                scores_df = pd.DataFrame(score_data).set_index('Brand')
                fig_hm = px.imshow(scores_df, text_auto=True, aspect="auto", color_continuous_scale='RdBu', title=f"Head-to-Head Scores ({latest_date})")
                st.plotly_chart(fig_hm, use_container_width=True)
                
                # --- EVIDENCE INSPECTOR ---
                with st.expander("🕵️ Evidence Inspector"):
                    if not scores_df.empty:
                        selected_brand = st.selectbox("Inspect Brand", scores_df.index.tolist())
                        if selected_brand:
                            b_scores = scores_df.loc[selected_brand].to_dict()
                            b_evidence = citations_map.get(selected_brand, {})
                            
                            inspect_data = []
                            for vec, score_val in b_scores.items():
                                evidence_url = b_evidence.get(vec, "N/A")
                                
                                # Render clickable link if it looks like a URL
                                if isinstance(evidence_url, str) and evidence_url.startswith("http"):
                                    link_md = f"[🔗 Open Source]({evidence_url})"
                                    context_text = "Direct Citation"
                                else:
                                    link_md = "N/A"
                                    context_text = str(evidence_url)
                                    
                                inspect_data.append({
                                    "Vector": vec, 
                                    "Score": score_val, 
                                    "Evidence Context": context_text,
                                    "Source Link": link_md
                                })
                            
                            df_inspect = pd.DataFrame(inspect_data)
                            st.markdown(df_inspect.to_markdown(index=False), unsafe_allow_html=True)
                            st.caption("ℹ️ 'Source Link' contains the exact URL the AI found while browsing.")
            else: st.info("No score data.")

        st.divider()
        
        col_c, col_d = st.columns(2)

        # 4. GAP ANALYSIS
        with col_c:
            st.subheader("4. Gap from Perfection")
            if not dff.empty:
                dff['total_distance'] = pd.to_numeric(dff['total_distance'], errors='coerce')
                dff['rank'] = pd.to_numeric(dff['rank'], errors='coerce')
                gap_df = dff.groupby('brand').agg({'total_distance': 'mean', 'rank': 'mean', 'type': 'first'}).reset_index().sort_values(by='total_distance')
                fig_gap = px.scatter(gap_df, x='brand', y='total_distance', size='rank', color='type', title="Avg Euclidean Distance", color_discrete_map={"Target": "red", "Competitor": "blue"})
                fig_gap.update_yaxes(range=[10, 0], title="Distance from Perfect 10")
                st.plotly_chart(fig_gap, use_container_width=True)

        # 5. STRATEGIC LANDSCAPE
        with col_d:
            st.subheader("5. Strategic Landscape")
            if not dff.empty:
                strat_df = dff.groupby('brand').agg({'total_distance': 'mean', 'rank': 'mean', 'brand': 'count'}).rename(columns={'brand': 'Mentions', 'total_distance': 'Avg_Distance', 'rank': 'Avg_Rank'}).reset_index()
                strat_df['Visibility_Score'] = strat_df['Mentions'] / strat_df['Avg_Rank']
                fig_strat = px.scatter(strat_df, x='Visibility_Score', y='Avg_Distance', color='Mentions', size='Mentions', title="Visibility vs. Performance")
                fig_strat.update_yaxes(range=[10, 0])
                st.plotly_chart(fig_strat, use_container_width=True)

        st.divider()

        # 6. DOMAIN POWER RANKINGS (Trust Weighted)
        st.subheader("6. Domain Power Rankings (Explicit Trust Scores)")
        domain_scores = {}
        source_counts = Counter() 
        if weights_json and details_json:
            try:
                weights_map = json.loads(weights_json)
                details = json.loads(details_json)
                for vec, weight_val in weights_map.items():
                    if weight_val == 0: continue
                    info = details.get(vec)
                    if not info:
                         for k in details:
                            if k.lower() == vec.lower(): info = details[k]; break
                    if info:
                        sources_data = info.get("key_sources", [])
                        if isinstance(sources_data, list) and len(sources_data) > 0 and isinstance(sources_data[0], dict):
                            total_conf = sum([i.get("score", 1) for i in sources_data]) or 1
                            for item in sources_data:
                                s_dom = item.get("domain", "Unknown").strip().lower()
                                s_score = item.get("score", 1)
                                domain_scores[s_dom] = domain_scores.get(s_dom, 0) + ((s_score / total_conf) * weight_val)
                                source_counts[s_dom] += 1
                        elif isinstance(sources_data, list) and len(sources_data) > 0 and isinstance(sources_data[0], str):
                             total_shares = sum([1/(i+1) for i in range(len(sources_data))])
                             for i, s_str in enumerate(sources_data):
                                 s_clean = s_str.strip().lower()
                                 domain_scores[s_clean] = domain_scores.get(s_clean, 0) + (weight_val * ((1/(i+1))/total_shares))
                                 source_counts[s_clean] += 1
            except: pass

        if domain_scores:
            power_data = [{"Domain": d, "Power Score": s, "Citations": source_counts[d]} for d, s in domain_scores.items()]
            df_power = pd.DataFrame(power_data).sort_values(by="Power Score", ascending=True).tail(15)
            
            t_a, t_b = st.tabs(["🏆 Power Chart", "🕸️ Attribution Map"])
            with t_a:
                fig_p = px.bar(df_power, x="Power Score", y="Domain", orientation='h', text="Citations", title="<b>Most Influential Domains</b>", color="Power Score", color_continuous_scale="Viridis")
                st.plotly_chart(fig_p, use_container_width=True)
            with t_b:
                sb_rows = []
                try:
                    w_map = json.loads(weights_json)
                    det = json.loads(details_json)
                    for vec, info in det.items():
                        w_val = w_map.get(vec, 0)
                        srcs = info.get("key_sources", [])
                        if srcs and isinstance(srcs[0], dict):
                            tot = sum([x.get("score", 1) for x in srcs]) or 1
                            for x in srcs:
                                sb_rows.append({"Vector": vec, "Source": x.get("domain"), "Size": (x.get("score", 1)/tot)*w_val})
                        elif srcs and isinstance(srcs[0], str):
                             tot = sum([1/(i+1) for i in range(len(srcs))])
                             for i, x in enumerate(srcs):
                                 sb_rows.append({"Vector": vec, "Source": x, "Size": (1/(i+1)/tot)*w_val})
                    if sb_rows:
                        fig_sb = px.sunburst(pd.DataFrame(sb_rows), path=['Vector', 'Source'], values='Size', title="<b>Weighted Attribution Map</b>")
                        st.plotly_chart(fig_sb, use_container_width=True)
                except: st.info("Sunburst unavailable.")
        else:
            st.info("Run new audit to see Domain Power Rankings.")
