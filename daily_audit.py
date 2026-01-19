import pandas as pd
import json
import os
import datetime
import google.generativeai as genai
from openai import OpenAI
from github_utils import load_config, load_history, save_history_csv

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")

def query_model(provider, prompt):
    try:
        if provider == "OpenAI" and OPENAI_KEY:
            client = OpenAI(api_key=OPENAI_KEY)
            response = client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2
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
        brand = target['brand']
        print(f"🚀 Auditing {brand}...")
        
        # PROMPT
        prompt = f"""
        Act as a Data Analyst. Audit '{brand}' (Category: {target['category']}) for '{target['use_case']}'.
        1. Identify top 5 critical decision vectors.
        2. Score '{brand}' (1-10) on these vectors.
        3. Calculate 'Total_Distance' (Euclidean Distance from Perfect 10).
        
        Output STRICT JSON:
        {{
            "vector_1_name": <score>,
            "vector_2_name": <score>,
            "vector_3_name": <score>,
            "vector_4_name": <score>,
            "vector_5_name": <score>,
            "Total_Distance": <score>
        }}
        """

        # Run against BOTH models
        for provider in ["OpenAI", "Gemini"]:
            res = query_model(provider, prompt)
            if res:
                try:
                    clean_json = res.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    row = {
                        "date": datetime.date.today(),
                        "brand": brand,
                        "category": target['category'],
                        "use_case": target['use_case'],
                        "model_provider": provider,
                        "total_distance": data.get("Total_Distance", 0),
                        "raw_json": json.dumps(data)
                    }
                    new_rows.append(row)
                except:
                    print(f"Failed to parse JSON for {provider}")

    if new_rows:
        current_df = load_history()
        new_df = pd.DataFrame(new_rows)
        combined = pd.concat([current_df, new_df], ignore_index=True)
        save_history_csv(combined)
        print("✅ Data Saved.")

if __name__ == "__main__":
    run_audit()
