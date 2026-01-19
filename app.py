import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from github_utils import load_config, save_config, load_history

st.set_page_config(page_title="GEO Enterprise", layout="wide")
st.title("🌍 GEO Enterprise Dashboard")

tab1, tab2 = st.tabs(["⚙️ Admin Config", "📊 Analytics Dashboard"])

# --- TAB 1: ADMIN ---
with tab1:
    st.header("Tracker Configuration")
    
    # Add New Target
    with st.form("add_target"):
        c1, c2, c3 = st.columns(3)
        brand = c1.text_input("Brand")
        cat = c2.text_input("Category")
        case = c3.text_input("Use Case")
        if st.form_submit_button("Add to Tracker"):
            current = load_config()
            current.append({"brand": brand, "category": cat, "use_case": case})
            save_config(current)
            st.success(f"Added {brand}!")
            st.rerun()

    # Show/Delete List
    targets = load_config()
    if targets:
        st.dataframe(pd.DataFrame(targets))
        if st.button("Reset Configuration (Clear All)"):
            save_config([])
            st.rerun()

# --- TAB 2: DASHBOARD ---
with tab2:
    st.header("Performance Analytics")
    df = load_history()
    
    if not df.empty:
        # Filters
        brands = df['brand'].unique()
        sel_brand = st.selectbox("Select Brand", brands)
        
        # Filter Data
        dff = df[df['brand'] == sel_brand]
        
        # 1. Trend Line
        st.subheader("1. Distance from Perfection")
        fig = px.line(dff, x="date", y="total_distance", color="model_provider", markers=True)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. Radar Chart (Latest Data)
        st.subheader("2. Vector Profile (Gemini vs OpenAI)")
        latest_date = dff['date'].max()
        latest = dff[dff['date'] == latest_date]
        
        fig_r = go.Figure()
        for i, row in latest.iterrows():
            try:
                j = json.loads(row['raw_json'])
                vecs = {k:v for k,v in j.items() if k != "Total_Distance"}
                fig_r.add_trace(go.Scatterpolar(
                    r=list(vecs.values()), theta=list(vecs.keys()), fill='toself', name=row['model_provider']
                ))
            except: pass
            
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
        st.plotly_chart(fig_r, use_container_width=True)
        
    else:
        st.info("No data yet. Go to Admin tab, add a target, and wait for the daily run.")
