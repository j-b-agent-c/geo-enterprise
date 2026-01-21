# --- DATA POINT 3: COMPETITIVE SCORECARD (With Evidence Inspector) ---
        st.subheader("3. Detailed Competitive Scorecard")
        
        if not latest_df.empty and 'vector_scores' in latest_df.columns:
            # A. The Heatmap (Overview)
            score_data = []
            citations_map = {} # Store citations for the inspector
            
            for idx, row in latest_df.iterrows():
                try:
                    scores = json.loads(row['vector_scores'])
                    scores['Brand'] = row['brand']
                    score_data.append(scores)
                    
                    # Store citations if available
                    if 'vector_citations' in row:
                        citations_map[row['brand']] = json.loads(row['vector_citations'])
                except:
                    continue
            
            if score_data:
                scores_df = pd.DataFrame(score_data)
                scores_df = scores_df.set_index('Brand')
                fig_hm = px.imshow(scores_df, text_auto=True, aspect="auto",
                                   color_continuous_scale='RdBu', 
                                   title=f"Head-to-Head: Brand Scores per Vector ({latest_date})")
                st.plotly_chart(fig_hm, use_container_width=True)
                
                # B. The Evidence Inspector (Drill Down)
                with st.expander("🕵️ Evidence Inspector: Why did a brand get this score?"):
                    selected_brand_inspect = st.selectbox("Select Brand to Inspect", scores_df.index.tolist())
                    
                    if selected_brand_inspect:
                        # 1. Get Scores
                        b_scores = scores_df.loc[selected_brand_inspect].to_dict()
                        
                        # 2. Get Citations (try/except for old data safety)
                        b_citations = citations_map.get(selected_brand_inspect, {})
                        
                        inspect_rows = []
                        for vec, score_val in b_scores.items():
                            citation_url = b_citations.get(vec, "N/A (Historical Data)")
                            inspect_rows.append({
                                "Vector": vec,
                                "Score": score_val,
                                "Evidence Source": citation_url
                            })
                        
                        df_inspect = pd.DataFrame(inspect_rows)
                        st.table(df_inspect)
            else:
                st.info("No detailed score data available.")
