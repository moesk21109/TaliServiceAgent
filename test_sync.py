"""Test script to call the sync endpoint."""
import requests
import sys

try:
    print("Sending POST request to http://127.0.0.1:8000/customers/sync-lexware")
    response = requests.post("http://127.0.0.1:8000/customers/sync-lexware", timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"JSON: {response.json()}")
except requests.exceptions.ConnectionError as e:
    print(f"Connection Error: {e}")
    sys.exit(1)
except requests.exceptions.Timeout as e:
    print(f"Timeout Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
