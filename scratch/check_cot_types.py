import requests

def test_url(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=10)
    print(f"URL: {url}, Status: {res.status_code}")

if __name__ == "__main__":
    test_url("https://www.cftc.gov/files/dea/history/deahist2025.zip")
    test_url("https://www.cftc.gov/files/dea/history/deahistfo2025.zip")
