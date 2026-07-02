import sys

def check():
    packages = ["yfinance", "pandas", "requests", "openbb", "cot-reports"]
    for p in packages:
        try:
            __import__(p)
            print(f"{p}: Installed")
        except ImportError:
            print(f"{p}: NOT Installed")

if __name__ == "__main__":
    check()
