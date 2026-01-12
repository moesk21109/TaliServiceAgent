"""Direct test of the chat endpoint with detailed error output"""
import requests
import traceback

# First start the server manually in another terminal!
# python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

try:
    print("Testing direct chat API call...")
    resp = requests.post(
        "http://127.0.0.1:8000/chat/messages",
        json={"content": "Hallo", "session_id": 4},
        timeout=30
    )
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
