import pandas as pd
import json
import os
import datetime
import math
from openai import OpenAI
from github_utils import load_config, load_history, save_history_csv

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

def run_audit():
    print("----- 🔍 DIAGNOSTIC MODE STARTED -----")
    
    # 1. CHECK FILES
    print(f"📂 Current Directory Files: {os.listdir('.')}")
    
    if os.path.exists("config.json"):
        print("✅ Found config.json local file.")
        with open("config.json", "r") as f:
            print(f"📄 Raw Config Content: {f.read()}")
    else:
        print("❌ config.json NOT found locally.")

    # 2. CHECK CONFIG LOAD
    targets = load_config()
    print(f"📊 Targets Loaded: {targets}")
    
    if not targets:
        print("⚠️ STOPPING: No targets found. Check your config.json syntax!")
        return

    # 3. CHECK API KEY
    if not OPENAI_KEY:
        print("❌ STOPPING: OPENAI_API_KEY is missing from Secrets!")
        return
    else:
        print(f"🔑 API Key Found: {OPENAI_API_KEY[:5]}...")

    # 4. RUN TEST QUERY
    print("🚀 Attempting OpenAI Connection...")
    client = OpenAI(api_key=OPENAI_KEY)
    
    new_rows = []
    
    for target in targets:
        my_brand = target.get('brand', 'Unknown')
        print(f"🔎 Auditing: {my_brand}")
        
        try:
            # Simple test query to verify connection + tools
            response = client.chat.completions.create(
                model="gpt-4o", 
                messages=[{"role": "user", "content": f"Return JSON with a fake score for {my_brand}"}],
                response_format={"type": "json_object"}
            )
            print("✅ OpenAI Responded!")
            
            # (If we get here, the connection works. We proceed with the real logic in the next update.)
            # For now, let's just create a dummy row to prove we can save the CSV.
            new_rows.append({
                "date": datetime.date.today(),
                "run_id": "TEST_RUN",
                "brand": my_brand,
                "category": target.get('category'),
                "use_case": target.get('use_case'),
                "type": "Target",
                "rank": 1,
                "vector_scores": "{}",
                "vector_citations": "{}"
            })
            
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")

    # 5. SAVE DATA
    if new_rows:
        print(f"💾 Saving {len(new_rows)} rows to history.csv...")
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        save_history_csv(pd.concat([current_df, new_df], ignore_index=True))
        print("✅ Data Saved Successfully.")
    else:
        print("⚠️ No new rows generated.")

if __name__ == "__main__":
    run_audit()
