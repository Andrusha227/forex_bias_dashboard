import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from scratch.backtest_data import load_cached_data
from scratch.backtest_engine import run_score_on_date

def main():
    print("Loading cached data...")
    cache = load_cached_data()
    
    eurusd = cache["eurusd"]
    # Filter dates
    test_dates = eurusd[eurusd["date"] >= "2021-09-01"].sort_values("date")["date"].dt.strftime("%Y-%m-%d").tolist()
    
    print(f"Total days to simulate: {len(test_dates)}")
    
    results = []
    
    count = 0
    total_days = len(test_dates)
    
    has_h4 = cache.get("h4") is not None
    h4_start_date = "2023-07-12" if has_h4 else "9999-12-31"
    
    for t_str in test_dates:
        count += 1
        if count % 100 == 0 or count == total_days:
            print(f"Simulating day {count}/{total_days} ({t_str})...")
            
        use_h4 = has_h4 and (t_str >= h4_start_date)
        res = run_score_on_date(cache, t_str, use_h4=use_h4)
        if res is not None:
            results.append(res)
            
    # Convert to DataFrame
    df_res = pd.DataFrame(results)
    print(f"Simulation completed. Evaluated {len(df_res)} days.")
    
    # Align forward returns
    eurusd_sorted = eurusd.sort_values("date").reset_index(drop=True)
    eurusd_sorted["date_str"] = eurusd_sorted["date"].dt.strftime("%Y-%m-%d")
    price_map = eurusd_sorted.set_index("date_str")["close"].to_dict()
    low_map = eurusd_sorted.set_index("date_str")["low"].to_dict()
    high_map = eurusd_sorted.set_index("date_str")["high"].to_dict()
    
    dates_list = eurusd_sorted["date_str"].tolist()
    date_to_index = {d: i for i, d in enumerate(dates_list)}
    
    forward_returns_1 = []
    forward_returns_3 = []
    forward_returns_5 = []
    forward_returns_10 = []
    max_drawdowns_10 = []
    
    for i, row in df_res.iterrows():
        dt = row["date"]
        close_price = row["close_price"]
        
        idx = date_to_index.get(dt)
        if idx is None:
            forward_returns_1.append(np.nan)
            forward_returns_3.append(np.nan)
            forward_returns_5.append(np.nan)
            forward_returns_10.append(np.nan)
            max_drawdowns_10.append(np.nan)
            continue
            
        # 1-day
        if idx + 1 < len(dates_list):
            p1 = price_map[dates_list[idx + 1]]
            forward_returns_1.append((p1 - close_price) / close_price)
        else:
            forward_returns_1.append(np.nan)
            
        # 3-day
        if idx + 3 < len(dates_list):
            p3 = price_map[dates_list[idx + 3]]
            forward_returns_3.append((p3 - close_price) / close_price)
        else:
            forward_returns_3.append(np.nan)
            
        # 5-day
        if idx + 5 < len(dates_list):
            p5 = price_map[dates_list[idx + 5]]
            forward_returns_5.append((p5 - close_price) / close_price)
        else:
            forward_returns_5.append(np.nan)
            
        # 10-day
        if idx + 10 < len(dates_list):
            p10 = price_map[dates_list[idx + 10]]
            forward_returns_10.append((p10 - close_price) / close_price)
        else:
            forward_returns_10.append(np.nan)
            
        # 10-day max drawdown
        next_10_dates = dates_list[idx + 1 : min(idx + 11, len(dates_list))]
        if next_10_dates:
            next_lows = [low_map[d] for d in next_10_dates]
            next_highs = [high_map[d] for d in next_10_dates]
            
            verdict = row["verdict"].lower()
            if "strong bullish" in verdict or "bullish" in verdict:
                dd = (min(next_lows) - close_price) / close_price
                max_drawdowns_10.append(min(0.0, dd))
            elif "strong bearish" in verdict or "bearish" in verdict:
                dd = (close_price - max(next_highs)) / close_price
                max_drawdowns_10.append(min(0.0, dd))
            else:
                max_drawdowns_10.append(np.nan)
        else:
            max_drawdowns_10.append(np.nan)
            
    df_res["ret_1d"] = forward_returns_1
    df_res["ret_3d"] = forward_returns_3
    df_res["ret_5d"] = forward_returns_5
    df_res["ret_10d"] = forward_returns_10
    df_res["max_dd_10d"] = max_drawdowns_10
    
    trade_returns = []
    for i, row in df_res.iterrows():
        v = row["verdict"].lower()
        r = row["ret_1d"]
        if pd.isna(r):
            trade_returns.append(np.nan)
            continue
            
        if "strong bullish" in v or "bullish" in v:
            trade_returns.append(r)
        elif "strong bearish" in v or "bearish" in v:
            trade_returns.append(-r)
        else:
            trade_returns.append(0.0)
            
    df_res["trade_ret_1d"] = trade_returns
    
    # Historical Volatility
    eurusd_sorted["ret"] = eurusd_sorted["close"].pct_change()
    eurusd_sorted["vol_20d"] = eurusd_sorted["ret"].rolling(20).std()
    vol_map = eurusd_sorted.set_index("date_str")["vol_20d"].to_dict()
    df_res["vol_20d"] = df_res["date"].map(vol_map)
    
    # Save backtest results to CSV
    os.makedirs("scratch", exist_ok=True)
    df_res.to_csv("scratch/backtest_results.csv", index=False)
    print("Saved backtest results to scratch/backtest_results.csv")
    
    # Calculate statistics per verdict
    categories = [
        "Strong Bullish EUR/USD",
        "Bullish EUR/USD",
        "Neutral / Mixed",
        "Bearish EUR/USD",
        "Strong Bearish EUR/USD"
    ]
    
    stats = []
    for cat in categories:
        df_cat = df_res[df_res["verdict"] == cat]
        n = len(df_cat)
        if n == 0:
            stats.append({
                "verdict": cat, "sample_size": 0,
                "avg_1d": np.nan, "avg_3d": np.nan, "avg_5d": np.nan, "avg_10d": np.nan,
                "win_1d": np.nan, "win_3d": np.nan, "win_5d": np.nan, "win_10d": np.nan,
                "avg_dd_10d": np.nan
            })
            continue
            
        avg_1 = df_cat["ret_1d"].mean()
        avg_3 = df_cat["ret_3d"].mean()
        avg_5 = df_cat["ret_5d"].mean()
        avg_10 = df_cat["ret_10d"].mean()
        
        if "bullish" in cat.lower():
            win_1 = (df_cat["ret_1d"] > 0).sum() / df_cat["ret_1d"].dropna().count() if df_cat["ret_1d"].dropna().count() > 0 else np.nan
            win_3 = (df_cat["ret_3d"] > 0).sum() / df_cat["ret_3d"].dropna().count() if df_cat["ret_3d"].dropna().count() > 0 else np.nan
            win_5 = (df_cat["ret_5d"] > 0).sum() / df_cat["ret_5d"].dropna().count() if df_cat["ret_5d"].dropna().count() > 0 else np.nan
            win_10 = (df_cat["ret_10d"] > 0).sum() / df_cat["ret_10d"].dropna().count() if df_cat["ret_10d"].dropna().count() > 0 else np.nan
        elif "bearish" in cat.lower():
            win_1 = (df_cat["ret_1d"] < 0).sum() / df_cat["ret_1d"].dropna().count() if df_cat["ret_1d"].dropna().count() > 0 else np.nan
            win_3 = (df_cat["ret_3d"] < 0).sum() / df_cat["ret_3d"].dropna().count() if df_cat["ret_3d"].dropna().count() > 0 else np.nan
            win_5 = (df_cat["ret_5d"] < 0).sum() / df_cat["ret_5d"].dropna().count() if df_cat["ret_5d"].dropna().count() > 0 else np.nan
            win_10 = (df_cat["ret_10d"] < 0).sum() / df_cat["ret_10d"].dropna().count() if df_cat["ret_10d"].dropna().count() > 0 else np.nan
        else:
            win_1 = (df_cat["ret_1d"] > 0).sum() / df_cat["ret_1d"].dropna().count() if df_cat["ret_1d"].dropna().count() > 0 else np.nan
            win_3 = (df_cat["ret_3d"] > 0).sum() / df_cat["ret_3d"].dropna().count() if df_cat["ret_3d"].dropna().count() > 0 else np.nan
            win_5 = (df_cat["ret_5d"] > 0).sum() / df_cat["ret_5d"].dropna().count() if df_cat["ret_5d"].dropna().count() > 0 else np.nan
            win_10 = (df_cat["ret_10d"] > 0).sum() / df_cat["ret_10d"].dropna().count() if df_cat["ret_10d"].dropna().count() > 0 else np.nan
            
        avg_dd = df_cat["max_dd_10d"].mean()
        
        stats.append({
            "verdict": cat,
            "sample_size": n,
            "avg_1d": avg_1, "avg_3d": avg_3, "avg_5d": avg_5, "avg_10d": avg_10,
            "win_1d": win_1, "win_3d": win_3, "win_5d": win_5, "win_10d": win_10,
            "avg_dd_10d": avg_dd
        })
        
    df_stats = pd.DataFrame(stats)
    
    # Core Evaluation Metrics
    active_signals = df_res[df_res["verdict"].str.lower().str.contains("bullish|bearish")]
    
    valid_active_5d = active_signals.dropna(subset=["ret_5d"])
    correct_5d = 0
    expectancy_5d_list = []
    
    for i, row in valid_active_5d.iterrows():
        v = row["verdict"].lower()
        r = row["ret_5d"]
        is_bull = "bullish" in v
        is_correct = (r > 0) if is_bull else (r < 0)
        if is_correct:
            correct_5d += 1
        expectancy_5d_list.append(r if is_bull else -r)
        
    accuracy_5d = correct_5d / len(valid_active_5d) if len(valid_active_5d) > 0 else np.nan
    expectancy_5d = np.mean(expectancy_5d_list) if expectancy_5d_list else np.nan
    
    valid_active_10d = active_signals.dropna(subset=["ret_10d"])
    correct_10d = 0
    expectancy_10d_list = []
    
    for i, row in valid_active_10d.iterrows():
        v = row["verdict"].lower()
        r = row["ret_10d"]
        is_bull = "bullish" in v
        is_correct = (r > 0) if is_bull else (r < 0)
        if is_correct:
            correct_10d += 1
        expectancy_10d_list.append(r if is_bull else -r)
        
    accuracy_10d = correct_10d / len(valid_active_10d) if len(valid_active_10d) > 0 else np.nan
    expectancy_10d = np.mean(expectancy_10d_list) if expectancy_10d_list else np.nan
    
    daily_trade_returns = df_res["trade_ret_1d"].dropna()
    mean_ret = daily_trade_returns.mean()
    std_ret = daily_trade_returns.std()
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else np.nan
    
    # Stability
    vol_median = df_res["vol_20d"].median()
    df_high_vol = df_res[df_res["vol_20d"] > vol_median]
    df_low_vol = df_res[df_res["vol_20d"] <= vol_median]
    
    def get_regime_metrics(df_sub):
        sub_active = df_sub[df_sub["verdict"].str.lower().str.contains("bullish|bearish")]
        valid_5d = sub_active.dropna(subset=["ret_5d"])
        correct = 0
        exp_list = []
        for i, row in valid_5d.iterrows():
            v = row["verdict"].lower()
            r = row["ret_5d"]
            is_bull = "bullish" in v
            is_correct = (r > 0) if is_bull else (r < 0)
            if is_correct:
                correct += 1
            exp_list.append(r if is_bull else -r)
            
        acc = correct / len(valid_5d) if len(valid_5d) > 0 else np.nan
        exp = np.mean(exp_list) if exp_list else np.nan
        
        trade_rets = df_sub["trade_ret_1d"].dropna()
        sh = (trade_rets.mean() / trade_rets.std()) * np.sqrt(252) if trade_rets.std() > 0 else np.nan
        return len(df_sub), len(sub_active), acc, exp, sh
        
    high_vol_metrics = get_regime_metrics(df_high_vol)
    low_vol_metrics = get_regime_metrics(df_low_vol)
    
    df_res["year"] = pd.to_datetime(df_res["date"]).dt.year
    years = sorted(df_res["year"].unique())
    year_stats = []
    for y in years:
        df_y = df_res[df_res["year"] == y]
        y_active = df_y[df_y["verdict"].str.lower().str.contains("bullish|bearish")]
        y_valid_5d = y_active.dropna(subset=["ret_5d"])
        correct = 0
        exp_list = []
        for i, row in y_valid_5d.iterrows():
            v = row["verdict"].lower()
            r = row["ret_5d"]
            is_bull = "bullish" in v
            is_correct = (r > 0) if is_bull else (r < 0)
            if is_correct:
                correct += 1
            exp_list.append(r if is_bull else -r)
            
        acc = correct / len(y_valid_5d) if len(y_valid_5d) > 0 else np.nan
        exp = np.mean(exp_list) if exp_list else np.nan
        
        trade_rets = df_y["trade_ret_1d"].dropna()
        sh = (trade_rets.mean() / trade_rets.std()) * np.sqrt(252) if trade_rets.std() > 0 else np.nan
        
        year_stats.append({
            "year": y,
            "sample_size": len(df_y),
            "active_signals": len(y_active),
            "accuracy_5d": acc,
            "expectancy_5d": exp,
            "sharpe": sh
        })
        
    df_year_stats = pd.DataFrame(year_stats)
    
    # Print results
    print("\n" + "="*60)
    print("                 EUR/USD BACKTEST RESULTS")
    print("="*60)
    print(f"Backtest Horizon: {df_res['date'].iloc[0]} to {df_res['date'].iloc[-1]}")
    print(f"Total trading days: {len(df_res)}")
    print(f"Total active signals: {len(active_signals)}")
    print("-"*60)
    print("VERDICT PERFORMANCE TABLE:")
    print(df_stats.to_string(index=False, formatters={
        "avg_1d": lambda x: f"{x*100:+.3f}%" if not pd.isna(x) else "N/A",
        "avg_3d": lambda x: f"{x*100:+.3f}%" if not pd.isna(x) else "N/A",
        "avg_5d": lambda x: f"{x*100:+.3f}%" if not pd.isna(x) else "N/A",
        "avg_10d": lambda x: f"{x*100:+.3f}%" if not pd.isna(x) else "N/A",
        "win_1d": lambda x: f"{x*100:.1f}%" if not pd.isna(x) else "N/A",
        "win_3d": lambda x: f"{x*100:.1f}%" if not pd.isna(x) else "N/A",
        "win_5d": lambda x: f"{x*100:.1f}%" if not pd.isna(x) else "N/A",
        "win_10d": lambda x: f"{x*100:.1f}%" if not pd.isna(x) else "N/A",
        "avg_dd_10d": lambda x: f"{x*100:.3f}%" if not pd.isna(x) else "N/A"
    }))
    print("-"*60)
    print("CORE EVALUATION METRICS:")
    print(f"5-day Directional Accuracy:  {accuracy_5d*100:.2f}%" if not pd.isna(accuracy_5d) else "5-day Directional Accuracy: N/A")
    print(f"5-day Expectancy per Signal: {expectancy_5d*100:+.3f}%" if not pd.isna(expectancy_5d) else "5-day Expectancy per Signal: N/A")
    print(f"10-day Directional Accuracy: {accuracy_10d*100:.2f}%" if not pd.isna(accuracy_10d) else "10-day Directional Accuracy: N/A")
    print(f"10-day Expectancy per Signal:{expectancy_10d*100:+.3f}%" if not pd.isna(expectancy_10d) else "10-day Expectancy per Signal: N/A")
    print(f"Annualized Sharpe Ratio:     {sharpe:.3f}" if not pd.isna(sharpe) else "Annualized Sharpe Ratio: N/A")
    print("-"*60)
    print("VOLATILITY REGIME STABILITY:")
    print(f"High Volatility Days: {high_vol_metrics[0]} | Active Signals: {high_vol_metrics[1]}")
    print(f"  5d Accuracy: {high_vol_metrics[2]*100:.2f}% | 5d Expectancy: {high_vol_metrics[3]*100:+.3f}% | Sharpe: {high_vol_metrics[4]:.3f}")
    print(f"Low Volatility Days: {low_vol_metrics[0]} | Active Signals: {low_vol_metrics[1]}")
    print(f"  5d Accuracy: {low_vol_metrics[2]*100:.2f}% | 5d Expectancy: {low_vol_metrics[3]*100:+.3f}% | Sharpe: {low_vol_metrics[4]:.3f}")
    print("-"*60)
    print("YEARLY STABILITY BREAKDOWN:")
    print(df_year_stats.to_string(index=False, formatters={
        "accuracy_5d": lambda x: f"{x*100:.1f}%" if not pd.isna(x) else "N/A",
        "expectancy_5d": lambda x: f"{x*100:+.3f}%" if not pd.isna(x) else "N/A",
        "sharpe": lambda x: f"{x:.3f}" if not pd.isna(x) else "N/A"
    }))
    print("-"*60)
    
    # Calculate detailed diagnostics on category/factor scores
    category_scores = {}
    factor_signals = {}
    for r in results:
        for cat in r.get("categories", []):
            cat_name = cat["name"]
            score = cat["score"]
            if score is not None:
                category_scores[cat_name] = category_scores.get(cat_name, []) + [score]
            for f in cat.get("factors", []):
                f_name = f["name"]
                f_sig = f["signal"]
                if f_sig is not None:
                    factor_signals[f_name] = factor_signals.get(f_name, []) + [f_sig]
                    
    print("DIAGNOSTIC - MEAN SCORES BY CATEGORY:")
    for cat_name, scores in sorted(category_scores.items()):
        print(f"  {cat_name:25s}: Mean Score = {sum(scores)/len(scores):+.4f} (Count: {len(scores)})")
        
    print("\nDIAGNOSTIC - MEAN SIGNALS BY FACTOR:")
    for f_name, sigs in sorted(factor_signals.items()):
        print(f"  {f_name:30s}: Mean Signal = {sum(sigs)/len(sigs):+.4f} (Count: {len(sigs)})")
    print("="*60)
    
if __name__ == "__main__":
    main()
