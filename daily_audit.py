import pandas as pd
import json
import os
import datetime
import math
import google.generativeai as genai
from openai import OpenAI
from github_utils import load_config, load_history, save_history_csv

# --- CONFIGURATION ---
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")

def calculate_euclidean(scores):
    """
    Calculates distance from a perfect 10 on all vectors.
    """
    if not scores:
        return 0
    # Sum of squared differences from 10
    sum_sq_diff = sum((10 - score)**2 for score in scores.values())
    return round(math.sqrt(sum_sq_diff), 2)

def query_model(provider, prompt):
    try:
        if provider == "OpenAI" and OPENAI_KEY:
            client = OpenAI(api_key=OPENAI_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"} 
            )
            return response.choices[0].message.content
        elif provider == "Gemini" and GOOGLE_KEY:
            genai.configure(api_key=GOOGLE_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model.generate_content(prompt).text
    except Exception as e:
        print(f"Error {provider}: {e}")
        return None

def run_audit():
    targets = load_config()
    if not targets:
        print("No targets found in config.")
        return

    new_rows = []
    
    for target in targets:
        my_brand = target['brand']
        category = target['category']
        use_case = target['use_case']
        
        print(f"🚀 Running Market Sweep for: {my_brand} in {category}...")
        
        # --- THE UPDATED MEGA-PROMPT (With Per-Brand Citations) ---
        prompt = f"""
        Act as a Search Ranking Algorithm & Market Analyst.
        User Query Context: "{use_case}" within the "{category}" market.

        OBJECTIVE:
        1. Identify the Top 5 Weighted Decision Vectors.
        2. Define vectors with Data Type, KPI, and GLOBAL Confidence-Scored Sources.
        3. Identify Top 10 Leading Brands.
        4. Score '{my_brand}' against these vectors.
        5. CRITICAL: For EVERY brand scored, provide specific "Citations" proving where that specific score came from.

        OUTPUT STRICT JSON FORMAT:
        {{
            "market_vectors": {{
                "Vector_Name_1": <weight_int>,
                "Vector_Name_2": <weight_int>
            }},
            "vector_definitions": {{
                "Vector_Name_1": {{ 
                    "type": "Quantitative", 
                    "kpi": "Price ($USD)", 
                    "key_sources": [
                        {{ "domain": "amazon.com", "score": 9 }},
                        {{ "domain": "nike.com", "score": 10 }}
                    ]
                }}
            }},
            "market_leaders": [
                {{ 
                    "rank": 1, 
                    "brand": "BrandA", 
                    "scores": {{ "Vector_Name_1": 8, "Vector_Name_2": 9 }},
                    "citations": {{ "Vector_Name_1": "amazon.com/branda-price", "Vector_Name_2": "reddit.com/r/running/branda-review" }}
                }},
                {{ 
                    "rank": 2, 
                    "brand": "BrandB", 
                    "scores": {{ "Vector_Name_1": 6, "Vector_Name_2": 7 }},
                    "citations": {{ "Vector_Name_1": "amazon.com/brandb-price", "Vector_Name_2": "youtube.com/brandb-review" }}
                }}
            ],
            "target_brand_analysis": {{
                "brand": "{my_brand}",
                "rank_context": <estimated_rank_int>,
                "scores": {{ "Vector_Name_1": 5, "Vector_Name_2": 8 }},
                "citations": {{ "Vector_Name_1": "amazon.com/mybrand-price", "Vector_Name_2": "mybrand.com/specs" }}
            }}
        }}
        """

        # Run against BOTH models
        for provider in ["OpenAI", "Gemini"]:
            res = query_model(provider, prompt)
            if res:
                try:
                    clean_json = res.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    # 1. Extract Shared Data
                    vectors = data.get("market_vectors", {})
                    vector_defs = data.get("vector_definitions", {})
                    
                    # Flatten global sources
                    all_sources = []
                    for v in vector_defs.values():
                        raw_sources = v.get("key_sources", [])
                        for s in raw_sources:
                            if isinstance(s, dict): all_sources.append(s.get("domain"))
                            elif isinstance(s, str): all_sources.append(s)

                    # 2. Process Target
                    target_data = data.get("target_brand_analysis", {})
                    target_scores = target_data.get("scores", {})
                    target_citations = target_data.get("citations", {}) # NEW
                    target_dist = calculate_euclidean(target_scores)
                    
                    # Common row data
                    row_base = {
                        "date": datetime.date.today(),
                        "run_id": f"{datetime.date.today()}_{my_brand}_{provider}",
                        "category": category,
                        "use_case": use_case,
                        "model_provider": provider,
                        "vector_weights": json.dumps(vectors),
                        "vector_details": json.dumps(vector_defs),
                        "sources": json.dumps(list(set(all_sources)))
                    }

                    # Add Target Row
                    new_rows.append({
                        **row_base,
                        "type": "Target",
                        "brand": my_brand,
                        "rank": target_data.get("rank_context", 11),
                        "total_distance": target_dist,
                        "vector_scores": json.dumps(target_scores),
                        "vector_citations": json.dumps(target_citations) # NEW COLUMN
                    })
                    
                    # 3. Process Competitors
                    for leader in data.get("market_leaders", [])[:10]:
                        l_brand = leader.get("brand")
                        if l_brand.lower() == my_brand.lower():
                            continue
                        
                        l_scores = leader.get("scores", {})
                        l_citations = leader.get("citations", {}) # NEW
                        l_dist = calculate_euclidean(l_scores)
                        
                        new_rows.append({
                            **row_base,
                            "type": "Competitor",
                            "brand": l_brand,
                            "rank": leader.get("rank"),
                            "total_distance": l_dist,
                            "vector_scores": json.dumps(l_scores),
                            "vector_citations": json.dumps(l_citations) # NEW COLUMN
                        })

                except Exception as e:
                    print(f"❌ Failed to parse JSON for {provider}: {e}")

    if new_rows:
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        combined = pd.concat([current_df, new_df], ignore_index=True)
        save_history_csv(combined)
        print("✅ Market Sweep Complete. Data Saved.")

if __name__ == "__main__":
    run_audit()
