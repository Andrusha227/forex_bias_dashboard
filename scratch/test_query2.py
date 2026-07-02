import requests
import json

def test_query2():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    # Test EURUSD=X chart endpoint (daily, 5 years)
    url_eurusd = "https://query2.finance.yahoo.com/v8/finance/chart/EURUSD=X?range=5y&interval=1d"
    res = requests.get(url_eurusd, headers=headers, timeout=10)
    print("EURUSD Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        result = data.get("chart", {}).get("result", [])
        if result:
            timestamps = result[0].get("timestamp", [])
            indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
            close = indicators.get("close", [])
            print("EURUSD rows:", len(timestamps))
            print("First date timestamp:", timestamps[0], "close:", close[0])
            print("Last date timestamp:", timestamps[-1], "close:", close[-1])

    # Test DX-Y.NYB (DXY Index)
    url_dxy = "https://query2.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?range=5y&interval=1d"
    res_dxy = requests.get(url_dxy, headers=headers, timeout=10)
    print("DXY Status:", res_dxy.status_code)
    if res_dxy.status_code == 200:
        data_dxy = res_dxy.json()
        result_dxy = data_dxy.get("chart", {}).get("result", [])
        if result_dxy:
            timestamps_dxy = result_dxy[0].get("timestamp", [])
            indicators_dxy = result_dxy[0].get("indicators", {}).get("quote", [{}])[0]
            close_dxy = indicators_dxy.get("close", [])
            print("DXY rows:", len(timestamps_dxy))
            print("First DXY timestamp:", timestamps_dxy[0], "close:", close_dxy[0])
            print("Last DXY timestamp:", timestamps_dxy[-1], "close:", close_dxy[-1])

if __name__ == "__main__":
    test_query2()
