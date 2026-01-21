# --- DATA POINT 2: VECTOR INTELLIGENCE (Filtered) ---
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
        
        if details_json:
            try:
                details = json.loads(details_json)
                weights_map = json.loads(weights_json) if weights_json else {}

                detail_rows = []
                for vec, info in details.items():
                    # Handle case sensitivity (try exact match, then lowercase)
                    weight_val = weights_map.get(vec)
                    if weight_val is None:
                        # Try finding a case-insensitive match
                        for w_key in weights_map:
                            if w_key.lower() == vec.lower():
                                weight_val = weights_map[w_key]
                                break
                    
                    # Default to 0 if still not found
                    if weight_val is None:
                        weight_val = 0

                    # FILTER: Skip 0% rows to keep the view clean
                    if weight_val == 0:
                        continue

                    detail_rows.append({
                        "Vector": vec,
                        "Weight": f"{weight_val}%",
                        "Type": info.get("type", "Unknown"),
                        "Sourcing Logic": info.get("source_logic", "N/A")
                    })
                
                if detail_rows:
                    # Sort by Weight (High to Low) for better readability
                    df_view = pd.DataFrame(detail_rows)
                    # Convert Weight string "30%" back to int 30 for sorting
                    df_view['_sort'] = df_view['Weight'].apply(lambda x: int(x.strip('%')))
                    df_view = df_view.sort_values(by='_sort', ascending=False).drop(columns=['_sort'])
                    
                    st.dataframe(df_view, hide_index=True, use_container_width=True)
                else:
                    st.caption("No significant vectors found (all weights were 0%).")
            except Exception as e:
                st.error(f"Error parsing DNA: {e}")
        else:
            if 'vector_details' in latest_df.columns:
                st.info("Waiting for next audit run to populate Vector DNA...")
            else:
                st.info("Run the updated Daily Audit to see Quantitative vs Qualitative breakdowns.")
