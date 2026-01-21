import pandas as pd
import json
import os
import base64
from github import Github, GithubException
import streamlit as st

# 1. AUTHENTICATION: Try Environment first (Action), then Streamlit Secrets (App)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("REPO_NAME")

if not GITHUB_TOKEN:
    try:
        GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    except:
        pass

if not REPO_NAME:
    try:
        REPO_NAME = st.secrets["REPO_NAME"]
    except:
        # FALLBACK: Replace this string with your actual "username/repo" if secrets fail
        REPO_NAME = "j-b-agent-c/geo-enterprise"

def get_repo():
    """Authenticates and returns the repository object."""
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN is missing.")
        return None
    try:
        g = Github(GITHUB_TOKEN)
        return g.get_repo(REPO_NAME)
    except Exception as e:
        print(f"❌ Error connecting to GitHub: {e}")
        return None

def load_config():
    """Loads targets from config.json in the repo."""
    try:
        repo = get_repo()
        if not repo: return []
        
        # Try to get the file from the repo
        try:
            contents = repo.get_contents("config.json")
            decoded = base64.b64decode(contents.content).decode("utf-8")
            return json.loads(decoded)
        except:
            # File doesn't exist yet, return empty list
            return []
    except Exception as e:
        print(f"⚠️ Config Load Error: {e}")
        return []

def save_config(new_data):
    """Pushes updated targets to config.json in the repo."""
    try:
        repo = get_repo()
        if not repo: 
            st.error("Cannot connect to repository. Check GITHUB_TOKEN.")
            return
        
        # Convert list to JSON string
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
            # File missing, create it
            repo.create_file(
                path="config.json",
                message="Create Tracker Config via Streamlit",
                content=json_str
            )
        print("✅ Config saved to GitHub.")
    except Exception as e:
        st.error(f"❌ Config Save Error: {e}")
        print(f"❌ Config Save Error: {e}")

def load_history():
    """Loads history.csv from repo or local file."""
    # 1. Try Local File (Best for GitHub Action context)
    if os.path.exists("history.csv"):
        try:
            return pd.read_csv("history.csv")
        except:
            pass

    # 2. Try GitHub API (Best for Streamlit context)
    try:
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
