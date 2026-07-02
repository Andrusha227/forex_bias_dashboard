import os
import io
import zipfile
import csv
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Ensure cache directory exists
CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

load_dotenv()

def fetch_yahoo_daily(symbol, filename):
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        print(f"Yahoo data for {symbol} already cached.")
        return pd.read_csv(filepath)
    
    print(f"Fetching Yahoo data for {symbol}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    # 5 years range
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code != 200:
        raise ValueError(f"Failed to fetch {symbol} from Yahoo Finance: {res.status_code}")
    
    data = res.json()
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise ValueError(f"No chart result for {symbol}")
        
    timestamps = result[0].get("timestamp", [])
    indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
    opens = indicators.get("open", [])
    highs = indicators.get("high", [])
    lows = indicators.get("low", [])
    closes = indicators.get("close", [])
    
    rows = []
    for i in range(len(timestamps)):
        # Convert unix timestamp to date string
        dt = datetime.utcfromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
        rows.append({
            "date": dt,
            "open": opens[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i]
        })
        
    df = pd.DataFrame(rows)
    # Remove rows where close or other prices are null
    df = df.dropna().reset_index(drop=True)
    df.to_csv(filepath, index=False)
    print(f"Cached {len(df)} rows for {symbol} to {filepath}.")
    return df

def fetch_twelve_h4(symbol="EUR/USD", filename="eurusd_h4.csv"):
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        print(f"Twelve Data H4 already cached.")
        return pd.read_csv(filepath)
    
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("No Twelve Data API Key found. Skipping Twelve Data H4 fetch.")
        return None
        
    print(f"Fetching Twelve Data H4 for {symbol}...")
    url = "https://api.twelvedata.com/time_series"
    response = requests.get(
        url,
        params={
            "symbol": symbol,
            "interval": "4h",
            "outputsize": 5000,
            "apikey": api_key,
            "format": "JSON"
        },
        timeout=15
    )
    if response.status_code != 200:
        raise ValueError(f"Twelve Data API failed: {response.status_code}")
        
    payload = response.json()
    if payload.get("status") == "error":
        raise ValueError(f"Twelve Data error: {payload.get('message')}")
        
    values = payload.get("values", [])
    rows = []
    for item in values:
        rows.append({
            "datetime": item["datetime"], # Local NY time usually, let's keep as is
            "open": float(item["open"]),
            "high": float(item["high"]),
            "low": float(item["low"]),
            "close": float(item["close"])
        })
        
    df = pd.DataFrame(rows)
    # Reverse so it is chronological (first is oldest)
    df = df.iloc[::-1].reset_index(drop=True)
    df.to_csv(filepath, index=False)
    print(f"Cached {len(df)} H4 rows for {symbol} to {filepath}.")
    return df

def fetch_fred_series(series_id):
    filename = f"fred_{series_id}.json"
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        # Already cached
        return
        
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY environment variable is required.")
        
    print(f"Fetching FRED series {series_id}...")
    url = "https://api.stlouisfed.org/fred/series/observations"
    response = requests.get(
        url,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "2021-01-01",
            "realtime_start": "2021-01-01",
            "sort_order": "asc"
        },
        timeout=15
    )
    if response.status_code != 200:
        raise ValueError(f"FRED API failed for {series_id}: {response.status_code}")
        
    payload = response.json()
    observations = payload.get("observations", [])
    
    # Save as JSON
    with open(filepath, "w") as f:
        json.dump(observations, f, indent=2)
    print(f"Cached {len(observations)} observations for {series_id} to {filepath}.")

def fetch_all_fred():
    from src.data.fred_catalog import FRED_SERIES
    # Collect all unique series IDs
    series_ids = set()
    for group_name, series_map in FRED_SERIES.items():
        for label, series_id in series_map.items():
            series_ids.add(series_id)
            
    # Also fetch DGS2 and DGS10 which might be duplicate, but let's make sure
    series_ids.add("DGS2")
    series_ids.add("DGS10")
    
    for s_id in sorted(series_ids):
        fetch_fred_series(s_id)

def fetch_cot_reports():
    filename = "cot_history.csv"
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        print("COT history already cached.")
        return pd.read_csv(filepath)
        
    print("Downloading historical COT files from CFTC...")
    headers = {"User-Agent": "Mozilla/5.0"}
    all_rows = []
    
    # We want 2021 through 2026
    current_year = datetime.now().year
    for year in range(2021, current_year + 1):
        url = f"https://www.cftc.gov/files/dea/history/deacot{year}.zip"
        print(f"Downloading COT zip for {year}...")
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(res.content))
            with z.open(z.namelist()[0]) as f:
                content = f.read().decode('utf-8', errors='ignore')
                reader = csv.reader(io.StringIO(content))
                for row in reader:
                    if row and row[0].strip() == "EURO FX - CHICAGO MERCANTILE EXCHANGE":
                        try:
                            as_of_str = row[2].strip()
                            non_commercial_long = int(row[8].strip())
                            non_commercial_short = int(row[9].strip())
                            change_long = int(row[38].strip())
                            change_short = int(row[39].strip())
                            
                            all_rows.append({
                                "as_of_date": as_of_str,
                                "net_position": non_commercial_long - non_commercial_short,
                                "weekly_change": change_long - change_short
                            })
                        except (IndexError, ValueError) as e:
                            print(f"Error parsing row in {year}: {e}")
        else:
            print(f"Failed to download COT zip for {year}: {res.status_code}")
            
    df = pd.DataFrame(all_rows)
    # Sort by date
    df["as_of_date"] = pd.to_datetime(df["as_of_date"])
    df = df.sort_values("as_of_date").reset_index(drop=True)
    df.to_csv(filepath, index=False)
    print(f"Cached {len(df)} COT rows to {filepath}.")
    return df

def load_cached_data():
    """Loads all cached data and returns a dict."""
    eurusd_df = pd.read_csv(os.path.join(CACHE_DIR, "eurusd_daily.csv"), parse_dates=["date"])
    dxy_df = pd.read_csv(os.path.join(CACHE_DIR, "dxy_daily.csv"), parse_dates=["date"])
    
    h4_path = os.path.join(CACHE_DIR, "eurusd_h4.csv")
    h4_df = pd.read_csv(h4_path, parse_dates=["datetime"]) if os.path.exists(h4_path) else None
    
    cot_df = pd.read_csv(os.path.join(CACHE_DIR, "cot_history.csv"), parse_dates=["as_of_date"])
    
    # Load FRED JSON files
    fred_data = {}
    for filename in os.listdir(CACHE_DIR):
        if filename.startswith("fred_") and filename.endswith(".json"):
            series_id = filename[5:-5]
            with open(os.path.join(CACHE_DIR, filename), "r") as f:
                fred_data[series_id] = json.load(f)
                
    return {
        "eurusd": eurusd_df,
        "dxy": dxy_df,
        "h4": h4_df,
        "cot": cot_df,
        "fred": fred_data
    }

def main():
    fetch_yahoo_daily("EURUSD=X", "eurusd_daily.csv")
    fetch_yahoo_daily("DX-Y.NYB", "dxy_daily.csv")
    fetch_twelve_h4()
    fetch_all_fred()
    fetch_cot_reports()
    print("All backtest data successfully fetched and cached!")

if __name__ == "__main__":
    main()
