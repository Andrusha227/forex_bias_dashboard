import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_twelve_h4():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("No API Key")
        return
    
    url = "https://api.twelvedata.com/time_series"
    # Let's try to fetch 5000 H4 rows (about 3 years of 4H data, since there are 6 H4 candles per day * 260 days = 1560 candles per year)
    response = requests.get(
        url,
        params={
            "symbol": "EUR/USD",
            "interval": "4h",
            "outputsize": 5000,
            "apikey": api_key,
            "format": "JSON"
        },
        timeout=15
    )
    print("Status Code:", response.status_code)
    payload = response.json()
    if payload.get("status") == "error":
        print("Error:", payload.get("message"))
    else:
        values = payload.get("values", [])
        print("Fetched H4 rows:", len(values))
        if values:
            print("First row:", values[0])
            print("Last row:", values[-1])

if __name__ == "__main__":
    check_twelve_h4()
