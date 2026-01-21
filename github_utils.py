import pandas as pd
import json
import os
import base64
from github import Github, GithubException
import streamlit as st

# TRY to get token from Streamlit Secrets (for the App)
# If not there, check Environment Variables (for the Action)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    try:
        GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    except:
        pass

# REPO_NAME: You must set this in Streamlit Secrets or find it dynamically
# Format: "username/repo-name"
REPO_NAME = os.environ.get("REPO_NAME")
if not REPO_NAME:
    try:
        REPO_NAME = st.secrets["REPO_NAME"]
    except:
        # Fallback for local testing or if variable missing
        REPO_NAME = "j-b-agent-c/geo-enterprise" 

def get_repo():
    if not GITHUB_TOKEN:
        print("⚠️ GitHub Token missing.")
        return None
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

def load_config():
    """Loads targets from config.json in the repo."""
    try:
        repo = get_repo()
        if not repo: return []
        
        contents = repo.get_contents("config.json")
        decoded = base64.b64decode(contents.content).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        print(f"⚠️ Config Load Error: {e}")
        return []

def save_config(new_data):
    """Pushes updated targets to config.json in the repo."""
    try:
        repo = get_repo()
        if not repo: return
        
        json_str = json.dumps(new_data, indent=2)
        
        # Check if file exists to decide Update vs Create
        try:
            contents = repo.get_contents("config.json")
            repo.update_file(
                path=contents.path,
                message="Update Tracker Config via Streamlit",
                content=json_str,
                sha=contents.sha
            )
        except GithubException:
            repo.create_file(
                path="config.json",
                message="Create Tracker Config via Streamlit",
                content=json_str
            )
        print("✅ Config saved to GitHub.")
    except Exception as e:
        print(f"❌ Config Save Error: {e}")

def load_history():
    """Loads history.csv from repo."""
    try:
        # Check local first (for Action context)
        if os.path.exists("history.csv"):
            return pd.read_csv("history.csv")
            
        # Fallback to API (for Streamlit context)
        repo = get_repo()
        if not repo: return pd.DataFrame()
        
        contents = repo.get_contents("history.csv")
        from io import StringIO
        csv_content = base64.b64decode(contents.content).decode("utf-8")
        return pd.read_csv(StringIO(csv_content))
    except:
        return pd.DataFrame()

def save_history_csv(df):
    """Saves history.csv locally (The Action's YAML handles the Push)."""
    df.to_csv("history.csv", index=False)
