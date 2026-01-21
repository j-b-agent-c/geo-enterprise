import pandas as pd
import json
import os
import datetime
import math
from openai import OpenAI
from github_utils import load_config, load_history, save_history_csv

# --- CONFIGURATION ---
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

def calculate_euclidean(scores):
    if not scores: return 0
    sum_sq_diff = sum((10 - score)**2 for score in scores.values())
    return round(math.sqrt(sum_sq_diff), 2)

def query_model(prompt):
    """
    Uses OpenAI's Chat Completion API with Native Web Search enabled.
    """
    if not OPENAI_KEY:
        print("❌ Error: Missing OpenAI API Key")
        return None

    client = OpenAI(api_key=OPENAI_KEY)

    try:
        # We use the standard chat completion endpoint
        # We request the 'web_search_preview' tool (Native Search)
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "You are a market researcher. You must use your web_search tool to find real facts and URLs. Output strict JSON."},
                {"role": "user", "content": prompt}
            ],
            # This enables the native browser capability
            tools=[{
                "type": "web_search_preview" 
            }],
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error querying OpenAI API: {e}")
        return None

def run_audit():
    targets = load_config()
    if not targets:
        print("No targets found.")
        return

    new_rows = []
    
    for target in targets:
        my_brand = target['brand']
        category = target['category']
        use_case = target['use_case']
        
        print(f"🚀 Auditing: {my_brand} in {category}...")
        
        prompt = f"""
        Context: "{use_case}" in "{category}".
        
        TASK:
        1. Search the web to identify Top 5 Decision Vectors and Top Competitors.
        2. Score '{my_brand}' vs Competitors (0-10).
        3. EVIDENCE: You MUST include the specific URLs you found during your web search in the 'evidence' field.
        
        OUTPUT JSON format:
        {{
            "market_vectors": {{ "Vector1": <weight>, ... }},
            "vector_definitions": {{
                "Vector1": {{ "kpi": "...", "key_sources": ["domain.com"] }} 
            }},
            "market_leaders": [
                {{ "brand": "CompA", "scores": {{...}}, "evidence": {{ "Vector1": "https://found-url.com" }} }}
            ],
            "target_brand_analysis": {{
                "brand": "{my_brand}",
                "scores": {{...}}, 
                "evidence": {{ "Vector1": "https://found-url.com" }}
            }}
        }}
        """

        res = query_model(prompt)
        
        if res:
            try:
                clean_json = res.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                # --- STANDARD DATA PARSING ---
                vectors = data.get("market_vectors", {})
                vector_defs = data.get("vector_definitions", {})
                
                all_sources = []
                for v in vector_defs.values():
                    raw = v.get("key_sources", [])
                    for s in raw:
                        if isinstance(s, str): all_sources.append(s)

                t_data = data.get("target_brand_analysis", {})
                row_base = {
                    "date": datetime.date.today(),
                    "run_id": f"{datetime.date.today()}_{my_brand}",
                    "category": category, 
                    "use_case": use_case,
                    "vector_weights": json.dumps(vectors),
                    "vector_details": json.dumps(vector_defs),
                    "sources": json.dumps(list(set(all_sources)))
                }
                
                new_rows.append({
                    **row_base,
                    "type": "Target",
                    "brand": my_brand,
                    "rank": t_data.get("rank_context", 5), 
                    "total_distance": calculate_euclidean(t_data.get("scores", {})),
                    "vector_scores": json.dumps(t_data.get("scores", {})),
                    "vector_citations": json.dumps(t_data.get("evidence", {}))
                })
                
                for leader in data.get("market_leaders", [])[:5]:
                    if leader['brand'].lower() == my_brand.lower(): continue
                    new_rows.append({
                        **row_base,
                        "type": "Competitor",
                        "brand": leader['brand'],
                        "rank": leader.get("rank", 1),
                        "total_distance": calculate_euclidean(leader.get("scores", {})),
                        "vector_scores": json.dumps(leader.get("scores", {})),
                        "vector_citations": json.dumps(leader.get("evidence", {}))
                    })

            except Exception as e:
                print(f"❌ JSON Error: {e}")

    if new_rows:
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        save_history_csv(pd.concat([current_df, new_df], ignore_index=True))
        print("✅ Audit Complete.")

if __name__ == "__main__":
    run_audit()
