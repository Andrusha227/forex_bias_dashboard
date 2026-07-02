import requests

def test_stooq_details():
    headers = {"User-Agent": "Mozilla/5.0"}
    for symbol in ["EURUSD", "eurusd", "DX.F", "dx.f"]:
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        res = requests.get(url, headers=headers, timeout=10)
        print(f"Symbol: {symbol}, Status: {res.status_code}, Length: {len(res.text)}")
        if res.status_code == 200:
            print("Snippet:", res.text[:200])

if __name__ == "__main__":
    test_stooq_details()
