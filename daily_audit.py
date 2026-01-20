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
                response_format={"type": "json_object"} # Force valid JSON
            )
            return response.choices[0].message.content
        elif provider == "Gemini" and GOOGLE_KEY:
            genai.configure(api_key=GOOGLE_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Gemini doesn't have a strict 'json_object' mode like OpenAI yet, 
            # so we rely on the prompt instructions.
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
        
        # --- THE NEW MEGA-PROMPT ---
        prompt = f"""
        Act as a Search Ranking Algorithm & Market Analyst.
        User Query Context: "{use_case}" within the "{category}" market.

        OBJECTIVE:
        1. Identify the Top 5 Weighted Decision Vectors (Criteria) users care about.
        2. Identify the Top 10 Leading Brands for this specific context.
        3. Score the specific target brand: '{my_brand}' against the SAME vectors.

        OUTPUT STRICT JSON FORMAT:
        {{
            "market_vectors": {{
                "Vector_Name_1": <weight_int_1_to_100>,
                "Vector_Name_2": <weight_int_1_to_100>
            }},
            "simulated_sources": ["domain1.com", "publication2.com"],
            "market_leaders": [
                {{ "rank": 1, "brand": "BrandA", "scores": {{ "Vector_1": <1-10>, ... }} }},
                {{ "rank": 2, "brand": "BrandB", "scores": {{ "Vector_1": <1-10>, ... }} }}
            ],
            "target_brand_analysis": {{
                "brand": "{my_brand}",
                "rank_context": <estimated_rank_int>,
                "scores": {{ "Vector_1": <1-10>, ... }}
            }}
        }}
        """

        # Run against BOTH models
        for provider in ["OpenAI", "Gemini"]:
            res = query_model(provider, prompt)
            if res:
                try:
                    # Clean JSON string (strip markdown if present)
                    clean_json = res.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    # 1. Extract Shared Data (Vectors & Sources)
                    vectors = data.get("market_vectors", {})
                    sources = data.get("simulated_sources", [])
                    
                    # 2. Process The Target Brand (Your Brand)
                    target_data = data.get("target_brand_analysis", {})
                    target_scores = target_data.get("scores", {})
                    target_dist = calculate_euclidean(target_scores)
                    
                    new_rows.append({
                        "date": datetime.date.today(),
                        "run_id": f"{datetime.date.today()}_{my_brand}_{provider}", # key to group data later
                        "type": "Target",
                        "brand": my_brand,
                        "category": category,
                        "use_case": use_case,
                        "model_provider": provider,
                        "rank": target_data.get("rank_context", 11),
                        "total_distance": target_dist,
                        "vector_scores": json.dumps(target_scores),
                        "vector_weights": json.dumps(vectors),
                        "sources": json.dumps(sources)
                    })
                    
                    # 3. Process Market Leaders (Competitors) - OPTIONAL
                    # We save them so you can build the "Share of Voice" charts
                    for leader in data.get("market_leaders", [])[:10]: # Top 10 only
                        l_brand = leader.get("brand")
                        # Skip if the leader is the target brand (don't duplicate)
                        if l_brand.lower() == my_brand.lower():
                            continue
                            
                        l_scores = leader.get("scores", {})
                        l_dist = calculate_euclidean(l_scores)
                        
                        new_rows.append({
                            "date": datetime.date.today(),
                            "run_id": f"{datetime.date.today()}_{my_brand}_{provider}",
                            "type": "Competitor",
                            "brand": l_brand,
                            "category": category,
                            "use_case": use_case,
                            "model_provider": provider,
                            "rank": leader.get("rank"),
                            "total_distance": l_dist,
                            "vector_scores": json.dumps(l_scores),
                            "vector_weights": json.dumps(vectors),
                            "sources": json.dumps(sources)
                        })

                except Exception as e:
                    print(f"❌ Failed to parse JSON for {provider}: {e}")

    if new_rows:
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        # Combine and Ensure columns match
        combined = pd.concat([current_df, new_df], ignore_index=True)
        save_history_csv(combined)
        print("✅ Market Sweep Complete. Data Saved.")

if __name__ == "__main__":
    run_audit()
