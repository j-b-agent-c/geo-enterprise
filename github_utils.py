from github import Github
import os
import json
import pandas as pd
import io
import streamlit as st # Added this import

# --- CONFIGURATION ---
# ⚠️ REPLACE WITH YOUR ACTUAL REPO NAME (e.g., "JasonSmith/geo-enterprise")
REPO_NAME = "j-b-agent-c/geo-enterprise" 

def get_repo():
    # 1. Try to get token from GitHub Actions (os.environ)
    token = os.environ.get("GH_TOKEN")
    
    # 2. If not found, try to get from Streamlit Cloud (st.secrets)
    if not token:
        try:
            token = st.secrets["GH_TOKEN"]
        except:
            token = None
            
    if not token:
        return None
        
    g = Github(token)
    return g.get_repo(REPO_NAME)

def load_config():
    try:
        repo = get_repo()
        contents = repo.get_contents("tracking_config.json")
        return json.loads(contents.decoded_content.decode())
    except:
        return [] 

def save_config(new_config):
    repo = get_repo()
    data_str = json.dumps(new_config, indent=2)
    try:
        contents = repo.get_contents("tracking_config.json")
        repo.update_file(contents.path, "Update Config", data_str, contents.sha)
    except:
        repo.create_file("tracking_config.json", "Create Config", data_str)

def load_history():
    try:
        repo = get_repo()
        contents = repo.get_contents("history.csv")
        return pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    except:
        return pd.DataFrame()

def save_history_csv(df):
    repo = get_repo()
    csv_content = df.to_csv(index=False)
    try:
        contents = repo.get_contents("history.csv")
        repo.update_file(contents.path, "📈 Daily Data Update", csv_content, contents.sha)
    except:
        repo.create_file("history.csv", "📈 Create History Log", csv_content)
