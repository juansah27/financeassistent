"""
Test fetching WhatsApp groups from bot
"""
import httpx
import os

def main():
    BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")
    
    print("=" * 60)
    print("Testing WhatsApp Groups Endpoint")
    print("=" * 60)
    print()
    print(f"Bot API URL: {BOT_API_URL}")
    print()
    
    try:
        print("📞 Calling /groups endpoint...")
        response = httpx.get(
            f"{BOT_API_URL}/groups",
            headers={
                "X-Webhook-Secret": WEBHOOK_SECRET
            },
            timeout=10.0
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(response.text)
        print()
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                groups = data.get("groups", [])
                print(f"✅ Found {len(groups)} WhatsApp groups:")
                for g in groups:
                    print(f"  - {g['name']} (Allowed: {g.get('isAllowed', 'N/A')})")
                    print(f"    ID: {g['id']}")
            else:
                print(f"❌ API returned success=false: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
