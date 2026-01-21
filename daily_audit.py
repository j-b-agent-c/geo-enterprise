import pandas as pd
import json
import os
import datetime
import math
from openai import OpenAI
from github_utils import load_config, load_history, save_history_csv

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

def calculate_euclidean(scores):
    if not scores: return 0
    sum_sq_diff = sum((10 - score)**2 for score in scores.values())
    return round(math.sqrt(sum_sq_diff), 2)

def query_model(prompt):
    if not OPENAI_KEY:
        print("❌ Error: Missing OpenAI API Key")
        return None
        
    client = OpenAI(api_key=OPENAI_KEY)
    
    try:
        # UNIVERSAL SETUP: Standard Chat API + Web Search Tool
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "You are a market researcher. Use the 'web_search_preview' tool to find real URLs. Output JSON."},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "web_search_preview"}], # Native Search
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def run_audit():
    targets = load_config()
    if not targets:
        print("⚠️ No targets found in config. Add a brand in the App first!")
        return

    new_rows = []
    print("🚀 Starting Audit...")
    
    for target in targets:
        my_brand = target['brand']
        category = target['category']
        use_case = target['use_case']
        print(f"🔎 Analyzing: {my_brand}...")
        
        prompt = f"""
        Context: "{use_case}" in "{category}".
        TASK:
        1. Search web for Top 5 Decision Vectors & Competitors.
        2. Score '{my_brand}' vs Competitors (0-10).
        3. EVIDENCE: You MUST include found URLs in 'evidence' field.
        
        OUTPUT JSON:
        {{
            "market_vectors": {{ "Vector1": <weight> }},
            "vector_definitions": {{ "Vector1": {{ "kpi": "...", "key_sources": ["domain.com"] }} }},
            "market_leaders": [ {{ "brand": "CompA", "scores": {{ "Vector1": 8 }}, "evidence": {{ "Vector1": "http://url" }} }} ],
            "target_brand_analysis": {{ "brand": "{my_brand}", "scores": {{ "Vector1": 5 }}, "evidence": {{ "Vector1": "http://url" }} }}
        }}
        """

        res = query_model(prompt)
        if res:
            try:
                data = json.loads(res)
                # ... (Parsing logic identical to previous versions) ...
                vectors = data.get("market_vectors", {})
                vector_defs = data.get("vector_definitions", {})
                t_data = data.get("target_brand_analysis", {})
                
                row_base = {
                    "date": datetime.date.today(),
                    "run_id": f"{datetime.date.today()}_{my_brand}",
                    "category": category,
                    "use_case": use_case,
                    "vector_weights": json.dumps(vectors),
                    "vector_details": json.dumps(vector_defs),
                    "sources": json.dumps([])
                }
                
                new_rows.append({
                    **row_base, "type": "Target", "brand": my_brand, "rank": 5,
                    "total_distance": calculate_euclidean(t_data.get("scores", {})),
                    "vector_scores": json.dumps(t_data.get("scores", {})),
                    "vector_citations": json.dumps(t_data.get("evidence", {}))
                })
                
                for leader in data.get("market_leaders", [])[:5]:
                    if leader['brand'].lower() == my_brand.lower(): continue
                    new_rows.append({
                        **row_base, "type": "Competitor", "brand": leader['brand'], "rank": 1,
                        "total_distance": calculate_euclidean(leader.get("scores", {})),
                        "vector_scores": json.dumps(leader.get("scores", {})),
                        "vector_citations": json.dumps(leader.get("evidence", {}))
                    })
            except Exception as e:
                print(f"⚠️ Parsing Error: {e}")

    if new_rows:
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        save_history_csv(pd.concat([current_df, new_df], ignore_index=True))
        print("✅ Data Saved to history.csv.")
    else:
        print("⚠️ No data generated.")

if __name__ == "__main__":
    run_audit()
