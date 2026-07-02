import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def test_twelve():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("No Twelve Data API Key found")
        return
    
    url = "https://api.twelvedata.com/time_series"
    # Try to fetch 1000 daily candles for EUR/USD
    response = requests.get(
        url,
        params={
            "symbol": "EUR/USD",
            "interval": "1day",
            "outputsize": 1000,
            "apikey": api_key,
            "format": "JSON"
        },
        timeout=10
    )
    print("Twelve Data status:", response.status_code)
    payload = response.json()
    if payload.get("status") == "error":
        print("Twelve Data error:", payload.get("message"))
    else:
        values = payload.get("values", [])
        print("Twelve Data fetched daily rows:", len(values))
        if values:
            print("First row:", values[0])
            print("Last row:", values[-1])

def test_fred():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("No FRED API Key found")
        return
    
    # Try to fetch DFF (Fed Funds Rate) observations
    url = "https://api.stlouisfed.org/fred/series/observations"
    response = requests.get(
        url,
        params={
            "series_id": "DFF",
            "api_key": api_key,
            "file_type": "json",
            "limit": 10
        },
        timeout=10
    )
    print("FRED status:", response.status_code)
    if response.status_code == 200:
        obs = response.json().get("observations", [])
        print("FRED fetched DFF rows:", len(obs))
        print("FRED observations sample:", obs[:2])

if __name__ == "__main__":
    test_twelve()
    test_fred()
