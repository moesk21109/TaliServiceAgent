
import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Testing API...")
    
    # 1. Health
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"Health: {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # 2. Sync Customers
    try:
        resp = requests.post(f"{BASE_URL}/customers/sync-lexware")
        print(f"Sync: {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"Sync failed: {e}")

    # 3. List Customers
    try:
        resp = requests.get(f"{BASE_URL}/customers")
        customers = resp.json()
        print(f"Customers: {len(customers)}")
        for c in customers:
            print(f" - {c['name']} (ID: {c['id']})")
    except Exception as e:
        print(f"List customers failed: {e}")

if __name__ == "__main__":
    test_api()
