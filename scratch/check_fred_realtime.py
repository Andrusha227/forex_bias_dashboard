import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_realtime():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print("No API Key")
        return

    series_id = "CPIAUCSL"
    url = "https://api.stlouisfed.org/fred/series/observations"
    response = requests.get(
        url,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "2024-01-01",
            "realtime_start": "2024-01-01",
            "sort_order": "asc"
        },
        timeout=10
    )
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        obs = response.json().get("observations", [])
        print(f"Fetched {len(obs)} observations for {series_id}")
        for o in obs[:10]:
            print(f"Obs Date: {o['date']}, Value: {o['value']}, Realtime Start: {o['realtime_start']}, Realtime End: {o['realtime_end']}")

if __name__ == "__main__":
    check_realtime()
