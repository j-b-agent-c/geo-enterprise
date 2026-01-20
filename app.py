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
        
        use_cases =
