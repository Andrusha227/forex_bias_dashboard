import requests
import zipfile
import io
import csv

def check_exact_names():
    url = "https://www.cftc.gov/files/dea/history/deacot2025.zip"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=15)
    if res.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(res.content))
        with z.open(z.namelist()[0]) as f:
            content = f.read().decode('utf-8', errors='ignore')
            reader = csv.reader(io.StringIO(content))
            names = set()
            for row in reader:
                if row and "EURO FX" in row[0]:
                    names.add(row[0].strip())
            print("Unique market names matching 'EURO FX':", names)

            # Let's count rows for each unique name
            z.seek(0) # reset
            # re-open zip file to parse again
            f2 = zipfile.ZipFile(io.BytesIO(res.content))
            with f2.open(f2.namelist()[0]) as file_obj:
                content2 = file_obj.read().decode('utf-8', errors='ignore')
                reader2 = csv.reader(io.StringIO(content2))
                counts = {}
                for row in reader2:
                    if row and "EURO FX" in row[0]:
                        name = row[0].strip()
                        counts[name] = counts.get(name, 0) + 1
                print("Row counts per name:", counts)

if __name__ == "__main__":
    check_exact_names()
