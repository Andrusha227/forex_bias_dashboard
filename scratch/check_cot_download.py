import requests
import zipfile
import io
import csv

def check_cot():
    url = "https://www.cftc.gov/files/dea/history/deahistfo2025.zip"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=15)
    print("Download Status:", res.status_code)
    if res.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(res.content))
        filenames = z.namelist()
        print("Files in zip:", filenames)
        if filenames:
            with z.open(filenames[0]) as f:
                content = f.read().decode('utf-8', errors='ignore')
                reader = csv.reader(io.StringIO(content))
                count = 0
                for row in reader:
                    if row and "EURO FX" in row[0]:
                        count += 1
                        if count <= 5:
                            print(f"Row {count}:")
                            print("  Market:", row[0])
                            print("  Date:", row[2] if len(row) > 2 else "N/A")
                            print("  NC Long:", row[8] if len(row) > 8 else "N/A")
                            print("  NC Short:", row[9] if len(row) > 9 else "N/A")
                            print("  Change Long:", row[38] if len(row) > 38 else "N/A")
                            print("  Change Short:", row[39] if len(row) > 39 else "N/A")
                print("Total EURO FX rows found in 2025:", count)

if __name__ == "__main__":
    check_cot()
