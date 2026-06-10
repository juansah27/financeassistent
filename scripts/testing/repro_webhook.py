
import os
import sys
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from app.main import app

client = TestClient(app)

def test_webhook():
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        print("WEBHOOK_SECRET not found in .env")
        return

    payload = {
        "message": "#beli esgoodaday 5k",
        "sender": "Test User",
        "sender_number": "628123456789",
        "group_name": "Happy Family 🥰",
        "group_id": "123456789@g.us",
        "timestamp": "2024-02-05T12:00:00Z",
        "message_id": "test_msg_id_1"
    }

    headers = {
        "X-Webhook-Secret": secret
    }

    print(f"Sending payload: {payload['message']}")
    
    try:
        response = client.post("/api/whatsapp/webhook", json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("SUCCESS: Webhook processed message.")
        else:
            print("FAILURE: Webhook returned error.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_webhook()
