"""Quick test to verify the server and chat functionality"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=" * 60)
    print("SCHNELLTEST DER API")
    print("=" * 60)
    
    # Test 1: Customers endpoint
    print("\n1. Teste /customers Endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/customers", timeout=5)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            customers = resp.json()
            print(f"   ✅ {len(customers)} Kunden gefunden")
            if customers:
                print(f"   Erster Kunde: {customers[0].get('name', 'N/A')}")
        else:
            print(f"   ❌ Fehler: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Server nicht erreichbar!")
        return False
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return False
    
    # Test 2: Chat sessions
    print("\n2. Teste /chat/customer/{id}/sessions Endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/chat/customer/1/sessions", timeout=5)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            sessions = resp.json()
            print(f"   ✅ {len(sessions)} Sessions gefunden")
            if sessions:
                session_id = sessions[0].get('id')
                print(f"   Nutze Session ID: {session_id}")
        else:
            print(f"   ❌ Fehler: {resp.text[:200]}")
            session_id = 4  # Fallback
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        session_id = 4
    
    # Test 3: Send a chat message
    print("\n3. Teste Chat-Nachricht senden...")
    try:
        message_data = {"content": "Hallo", "session_id": session_id}
        resp = requests.post(
            f"{BASE_URL}/chat/messages",
            json=message_data,
            timeout=120
        )
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   ✅ Antwort erhalten!")
            print(f"   AI Response (erste 500 Zeichen):")
            ai_response = result.get('ai_response', {}).get('content', 'N/A')
            print(f"   {ai_response[:500]}...")
        else:
            print(f"   ❌ Fehler (Status {resp.status_code}):")
            try:
                error_detail = resp.json()
                print(f"   {json.dumps(error_detail, indent=2, ensure_ascii=False)[:1000]}")
            except:
                print(f"   {resp.text[:1000]}")
    except requests.exceptions.Timeout:
        print("   ⏱️ Timeout - AI braucht lange (OpenAI überlastet?)")
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
    
    print("\n" + "=" * 60)
    print("TEST ABGESCHLOSSEN")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_api()
