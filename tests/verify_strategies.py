import requests

BASE_URL = "http://localhost:1218"

def test_strategies():
    print("Listing strategies...")
    res = requests.get(f"{BASE_URL}/strategies")
    print(res.status_code, res.json())
    
    # Save a test strategy
    print("Saving test strategy...")
    payload = {
        "name": "test_strat",
        "code": "print('Hello World')",
        "params": {}
    }
    res = requests.post(f"{BASE_URL}/strategies", json=payload)
    print(res.status_code, res.json())
    
    # Verify file exists
    import os
    if os.path.exists("resources/strategies/test_strat.py"):
        print("File created successfully.")
    else:
        print("File NOT found.")

    # Get strategy
    print("Getting strategy...")
    res = requests.get(f"{BASE_URL}/strategies/test_strat")
    print(res.status_code, res.json())

if __name__ == "__main__":
    test_strategies()
