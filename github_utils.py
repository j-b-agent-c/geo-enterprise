from github import Github
import os
import json
import pandas as pd
import io

# --- CONFIGURATION ---
# ⚠️ REPLACE 'YOUR_USERNAME' WITH YOUR ACTUAL GITHUB USERNAME BELOW
REPO_NAME = "j-b-agent-c/geo-enterprise" 

def get_repo():
    # We grab the token from secrets
    token = os.environ.get("GH_TOKEN")
    if not token: 
        return None
    g = Github(token)
    return g.get_repo(REPO_NAME)

def load_config():
    """Load the list of brands to track"""
    try:
        repo = get_repo()
        contents = repo.get_contents("tracking_config.json")
        return json.loads(contents.decoded_content.decode())
    except:
        return [] # Return empty list if file doesn't exist

def save_config(new_config):
    """Save updated brand list"""
    repo = get_repo()
    data_str = json.dumps(new_config, indent=2)
    try:
        contents = repo.get_contents("tracking_config.json")
        repo.update_file(contents.path, "Update Config", data_str, contents.sha)
    except:
        repo.create_file("tracking_config.json", "Create Config", data_str)

def load_history():
    """Load the historical data CSV"""
    try:
        repo = get_repo()
        contents = repo.get_contents("history.csv")
        return pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    except:
        return pd.DataFrame()

def save_history_csv(df):
    """Save the updated history CSV"""
    repo = get_repo()
    csv_content = df.to_csv(index=False)
    try:
        contents = repo.get_contents("history.csv")
        repo.update_file(contents.path, "📈 Daily Data Update", csv_content, contents.sha)
    except:
        repo.create_file("history.csv", "📈 Create History Log", csv_content)
