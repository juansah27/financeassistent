"""
Test the Debt API endpoints
Run this to verify the API is working correctly
"""
import requests
import json

# Base URL for the API (adjust if needed)
BASE_URL = "http://localhost:8000"

# Note: You'll need to authenticate first to get cookies/token
# For now, we'll just test the parse endpoint structure

def test_parse_endpoint():
    """Test the /api/debt/parse endpoint"""
    print("\n" + "="*80)
    print("TESTING /api/debt/parse ENDPOINT")
    print("="*80)
    
    test_cases = [
        "Hutang ke Andi 3 juta",
        "Bayar cicilan motor 1,2jt",
        "Shopee PayLater 500 ribu",
        "Kartu kredit BCA 2 juta",
    ]
    
    for text in test_cases:
        print(f"\nInput: {text}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/debt/parse",
                json={"text": text},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Status: {response.status_code}")
                print(f"  Intent: {result['intent']}")
                print(f"  Confidence: {result['confidence']}")
                print(f"  Debt Type: {result['debt']['type']}")
                if result['debt']['total_amount']:
                    print(f"  Amount: Rp {result['debt']['total_amount']:,}")
            else:
                print(f"✗ Error: {response.status_code}")
                print(f"  Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("✗ Connection Error: Make sure the app is running on port 8000")
            print("  Try: docker-compose up -d")
            break
        except Exception as e:
            print(f"✗ Error: {e}")

def print_usage():
    """Print usage instructions"""
    print("\n" + "="*80)
    print("DEBT API USAGE EXAMPLES")
    print("="*80)
    
    print("\n1. Parse Natural Language Input:")
    print("   curl -X POST http://localhost:8000/api/debt/parse \\")
    print("     -H 'Content-Type: application/json' \\")
    print('     -d \'{"text": "Hutang ke Andi 3 juta"}\'')
    
    print("\n2. Create Debt:")
    print("   curl -X POST http://localhost:8000/api/debt \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "type": "personal",')
    print('       "creditor": "Andi",')
    print('       "total_amount": 3000000,')
    print('       "currency": "IDR"')
    print("     }'")
    
    print("\n3. List All Debts:")
    print("   curl http://localhost:8000/api/debt")
    
    print("\n4. Record Payment:")
    print("   curl -X POST http://localhost:8000/api/debt/1/pay \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "amount": 1000000,')
    print('       "notes": "Pembayaran pertama"')
    print("     }'")
    
    print("\n5. Get Debt Summary:")
    print("   curl http://localhost:8000/api/debt/summary/stats")
    print()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DEBT API TEST SUITE")
    print("="*80)
    
    # Test parse endpoint
    test_parse_endpoint()
    
    # Print usage
    print_usage()
    
    print("\n" + "="*80)
    print("Note: Full API testing requires authentication.")
    print("The parse endpoint should work without auth if configured.")
    print("="*80 + "\n")
