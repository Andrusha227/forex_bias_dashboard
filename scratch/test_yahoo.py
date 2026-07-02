import requests
import pandas as pd
import time

def test_yahoo():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    # EUR/USD from Yahoo Finance
    # From year 2020 (1577836800) to now (approx 1782782400)
    url_eurusd = "https://query1.finance.yahoo.com/v7/finance/download/EURUSD=X?period1=1577836800&period2=1782782400&interval=1d&events=history&includeAdjustedClose=true"
    res = requests.get(url_eurusd, headers=headers, timeout=10)
    print("EURUSD=X Yahoo Status:", res.status_code)
    if res.status_code == 200:
        df = pd.read_csv(requests.compat.StringIO(res.text))
        print("EURUSD=X rows:", len(df))
        print(df.head(2))
        print(df.tail(2))

    # DXY from Yahoo Finance (DX-Y.NYB)
    url_dxy = "https://query1.finance.yahoo.com/v7/finance/download/DX-Y.NYB?period1=1577836800&period2=1782782400&interval=1d&events=history&includeAdjustedClose=true"
    res_dxy = requests.get(url_dxy, headers=headers, timeout=10)
    print("DX-Y.NYB Yahoo Status:", res_dxy.status_code)
    if res_dxy.status_code == 200:
        df_dxy = pd.read_csv(requests.compat.StringIO(res_dxy.text))
        print("DX-Y.NYB rows:", len(df_dxy))
        print(df_dxy.head(2))
        print(df_dxy.tail(2))

if __name__ == "__main__":
    test_yahoo()
