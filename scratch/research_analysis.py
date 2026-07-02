import os
import pandas as pd
import numpy as np
import datetime

def parse_categories_from_row(cat_str):
    if pd.isna(cat_str):
        return {}
    try:
        allowed_globals = {
            "Timestamp": pd.Timestamp,
            "datetime": datetime,
            "nan": np.nan,
            "None": None,
            "True": True,
            "False": False
        }
        cats = eval(cat_str, allowed_globals, {})
        flat = {}
        for cat in cats:
            flat[cat["name"]] = cat["score"]
            for f in cat.get("factors", []):
                flat[f["name"]] = f["signal"]
        return flat
    except Exception as e:
        return {}

def run_analysis():
    df = pd.read_csv("scratch/backtest_results.csv")
    
    # 1. Parse categories and factors from the string column
    print("Parsing detailed categories and factors...")
    parsed_rows = []
    for idx, row in df.iterrows():
        p_dict = parse_categories_from_row(row["categories"])
        parsed_rows.append(p_dict)
    df_factors = pd.DataFrame(parsed_rows)
    df_full = pd.concat([df, df_factors], axis=1)
    
    print(f"Loaded {len(df_full)} rows from backtest results.")
    
    # --- 1. Raw Score Shifts and Predictive Power ---
    print("\n--- 1. Raw Score Shifts & Predictive Power ---")
    
    # Check simple correlation
    corr_5d = df_full["normalized_score"].corr(df_full["ret_5d"])
    corr_10d = df_full["normalized_score"].corr(df_full["ret_10d"])
    print(f"Correlation between Normalized Score and subsequent 5d Return: {corr_5d:.4f}")
    print(f"Correlation between Normalized Score and subsequent 10d Return: {corr_10d:.4f}")
    
    # Check score changes (momentum / shift)
    df_full["score_diff_5d"] = df_full["normalized_score"].diff(5)
    df_full["score_diff_10d"] = df_full["normalized_score"].diff(10)
    
    corr_shift_5d = df_full["score_diff_5d"].corr(df_full["ret_5d"])
    corr_shift_10d = df_full["score_diff_10d"].corr(df_full["ret_10d"])
    print(f"Correlation between 5d Score Shift and subsequent 5d Return: {corr_shift_5d:.4f}")
    print(f"Correlation between 10d Score Shift and subsequent 10d Return: {corr_shift_10d:.4f}")
    
    # Binned returns
    # Divide the score into 4 bins since the range is biased
    bins = [-1.0, -0.6, -0.2, 0.2, 1.0]
    labels = ["[-1.0, -0.6)", "[-0.6, -0.2)", "[-0.2, 0.2)", "[0.2, 1.0]"]
    df_full["score_bin"] = pd.cut(df_full["normalized_score"], bins=bins, labels=labels)
    
    print("\nBinned Performance Table (5d Forward Returns):")
    bin_stats = df_full.groupby("score_bin").agg(
        sample_size=("ret_5d", "count"),
        avg_ret_5d=("ret_5d", "mean"),
        win_rate_5d=("ret_5d", lambda x: (x > 0).sum() / x.count() if x.count() > 0 else np.nan)
    ).reset_index()
    print(bin_stats.to_string(index=False, formatters={"avg_ret_5d": lambda x: f"{x*100:+.3f}%", "win_rate_5d": lambda x: f"{x*100:.1f}%"}))
    
    # --- 2. DXY Direction vs Monthly Open Range Interaction ---
    print("\n--- 2. DXY Direction & Monthly Open Range Interaction ---")
    
    # Monthly range state is in Monthly Opening Range factor (which gives signal: +1.0, -0.5, etc.)
    # Let's extract raw signals
    # DXY Direction signal is in 'DXY Direction' factor (falling = 1.0, rising = -1.0)
    # Monthly Opening Range signal is in 'Monthly Opening Range' factor
    if "DXY Direction" in df_full.columns and "Monthly Opening Range" in df_full.columns:
        valid_interaction = df_full.dropna(subset=["DXY Direction", "Monthly Opening Range", "ret_5d"])
        
        # Define states
        # DXY Direction: 1.0 is EUR bullish (falling DXY), -1.0 is EUR bearish (rising DXY)
        # Monthly Opening Range:
        #   +1.0: Struck above range (Raid low occurred, EUR Bullish continuation)
        #   -0.5: Above range but clean target (EUR Bearish pull back/target)
        #   -1.0: Struck below range (Raid high occurred, EUR Bearish continuation)
        #   +0.5: Below range but clean target (EUR Bullish pull back/target)
        
        joint_stats = valid_interaction.groupby(["DXY Direction", "Monthly Opening Range"]).agg(
            sample_size=("ret_5d", "count"),
            avg_ret_5d=("ret_5d", "mean"),
            win_rate_5d=("ret_5d", lambda x: (x > 0).sum() / x.count() if x.count() > 0 else np.nan)
        ).reset_index()
        
        # Translate codes to readable names
        dxy_lbl = {1.0: "DXY Falling (EUR+)", -1.0: "DXY Rising (EUR-)", 0.0: "DXY Flat"}
        mor_lbl = {
            1.0: "Above + Raid Low (+1.0)",
            -0.5: "Above + Clean Target (-0.5)",
            -1.0: "Below + Raid High (-1.0)",
            0.5: "Below + Clean Target (+0.5)",
            0.0: "Inside Range (0.0)"
        }
        joint_stats["DXY State"] = joint_stats["DXY Direction"].map(dxy_lbl)
        joint_stats["Monthly Range State"] = joint_stats["Monthly Opening Range"].map(mor_lbl)
        
        print(joint_stats[["DXY State", "Monthly Range State", "sample_size", "avg_ret_5d", "win_rate_5d"]].to_string(index=False, formatters={
            "avg_ret_5d": lambda x: f"{x*100:+.3f}%",
            "win_rate_5d": lambda x: f"{x*100:.1f}%"
        }))
    else:
        print("Required factors (DXY Direction or Monthly Opening Range) not found in parsed columns.")
        
    # --- 3. COT Net Position shifts ---
    print("\n--- 3. COT Net Position Shifts ---")
    # We want to check if COT Net Position shifts predict monthly reversals.
    # Let's extract COT Net Position signals
    if "COT Net Position" in df_full.columns:
        # In results, COT Net Position signal is +1 (positive) or -1 (negative)
        # But we also have the raw COT net position inside the cot_history file.
        # Let's read from the cache directly to analyze the raw positions!
        from scratch.backtest_data import CACHE_DIR
        cot_history = pd.read_csv(os.path.join(CACHE_DIR, "cot_history.csv"))
        cot_history["as_of_date"] = pd.to_datetime(cot_history["as_of_date"])
        
        # Calculate 4-week difference in net position (buying/selling momentum)
        cot_history["net_pos_diff_4w"] = cot_history["net_position"].diff(4)
        
        # Merge with EUR/USD daily price history
        eurusd = pd.read_csv(os.path.join(CACHE_DIR, "eurusd_daily.csv"))
        eurusd["date"] = pd.to_datetime(eurusd["date"])
        
        # We merge COT on the release date (as_of_date + 3 days)
        cot_history["release_date"] = cot_history["as_of_date"] + pd.Timedelta(days=3)
        merged_cot = pd.merge_asof(
            eurusd.sort_values("date"),
            cot_history.sort_values("release_date"),
            left_on="date",
            right_on="release_date",
            direction="backward"
        )
        
        # Calculate subsequent 20-day returns (approx 1 month)
        merged_cot["ret_20d"] = merged_cot["close"].pct_change(20).shift(-20)
        merged_cot = merged_cot.dropna(subset=["net_pos_diff_4w", "ret_20d"])
        
        corr_cot_reversal = merged_cot["net_pos_diff_4w"].corr(merged_cot["ret_20d"])
        print(f"Correlation between 4-week COT Net Position shift and subsequent 20d Return: {corr_cot_reversal:.4f}")
        
        # Divide COT shifts into extreme buying vs extreme selling (percentiles)
        p10 = merged_cot["net_pos_diff_4w"].quantile(0.10)
        p90 = merged_cot["net_pos_diff_4w"].quantile(0.90)
        
        extreme_selling = merged_cot[merged_cot["net_pos_diff_4w"] <= p10]
        extreme_buying = merged_cot[merged_cot["net_pos_diff_4w"] >= p90]
        
        print(f"Extreme Selling Threshold (10th percentile): {p10:,.0f} contracts")
        print(f"  Sample size: {len(extreme_selling)} | Avg 20d Return: {extreme_selling['ret_20d'].mean()*100:+.3f}% | Win Rate (Short/Negative Return): {(extreme_selling['ret_20d'] < 0).sum()/len(extreme_selling)*100:.1f}%")
        
        print(f"Extreme Buying Threshold (90th percentile): {p90:,.0f} contracts")
        print(f"  Sample size: {len(extreme_buying)} | Avg 20d Return: {extreme_buying['ret_20d'].mean()*100:+.3f}% | Win Rate (Long/Positive Return): {(extreme_buying['ret_20d'] > 0).sum()/len(extreme_buying)*100:.1f}%")
    else:
        print("COT factors not found.")
        
if __name__ == "__main__":
    run_analysis()
