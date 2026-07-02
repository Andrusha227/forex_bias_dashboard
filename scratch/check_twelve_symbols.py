import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_twelve_symbols():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("No API Key")
        return
    
    url = "https://api.twelvedata.com/time_series"
    for symbol in ["DXY", "USDX", "DX", "UUP", "EUR/USD"]:
        response = requests.get(
            url,
            params={
                "symbol": symbol,
                "interval": "1day",
                "outputsize": 10,
                "apikey": api_key,
                "format": "JSON"
            },
            timeout=10
        )
        payload = response.json()
        print(f"Symbol: {symbol}, Status Code: {response.status_code}")
        if payload.get("status") == "error":
            print(f"  Error: {payload.get('message')}")
        else:
            print(f"  Success! Rows fetched: {len(payload.get('values', []))}")
            if payload.get('values'):
                print(f"  Sample: {payload['values'][0]}")

if __name__ == "__main__":
    check_twelve_symbols()
