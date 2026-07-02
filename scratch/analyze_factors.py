import pandas as pd
import json
import ast

def analyze():
    df = pd.read_csv("scratch/backtest_results.csv")
    
    # We want to extract categories and factors
    # The columns are: date, close_price, normalized_score, verdict, categories, total
    # categories is a string representation of a list of dicts:
    # [{'name': 'Monthly Structure', 'score': ..., 'factors': [{'name': '...', 'signal': ...}, ...]}, ...]
    
    factor_signals = {}
    category_scores = {}
    
    for i, row in df.iterrows():
        cats_str = row["categories"]
        if pd.isna(cats_str):
            continue
        try:
            # Safely evaluate string representation of python list
            cats = ast.literal_eval(cats_str)
            for cat in cats:
                cat_name = cat["name"]
                cat_score = cat["score"]
                if cat_score is not None:
                    category_scores[cat_name] = category_scores.get(cat_name, []) + [cat_score]
                
                for factor in cat.get("factors", []):
                    f_name = factor["name"]
                    f_sig = factor["signal"]
                    if f_sig is not None:
                        factor_signals[f_name] = factor_signals.get(f_name, []) + [f_sig]
        except Exception as e:
            print("Error parsing row:", e)
            break
            
    print("="*60)
    print("           AVERAGE CATEGORY AND FACTOR SCORES")
    print("="*60)
    print("CATEGORIES:")
    for cat_name, scores in category_scores.items():
        print(f"  {cat_name:25s}: Mean Score = {sum(scores)/len(scores):+.4f}, Count = {len(scores)}")
        
    print("\nFACTORS:")
    for f_name, sigs in sorted(factor_signals.items()):
        print(f"  {f_name:30s}: Mean Signal = {sum(sigs)/len(sigs):+.4f}, Count = {len(sigs)}")
    print("="*60)

if __name__ == "__main__":
    analyze()
