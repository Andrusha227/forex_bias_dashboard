import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def test_fred_history():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("No API Key")
        return

    series_id = "DFF"
    url = "https://api.stlouisfed.org/fred/series/observations"
    response = requests.get(
        url,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "2021-01-01",
            "sort_order": "asc"
        },
        timeout=10
    )
    print("FRED Status:", response.status_code)
    if response.status_code == 200:
        obs = response.json().get("observations", [])
        print(f"Fetched {len(obs)} observations for {series_id}")
        if obs:
            print("First:", obs[0])
            print("Last:", obs[-1])

if __name__ == "__main__":
    test_fred_history()
