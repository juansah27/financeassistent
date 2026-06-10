import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.services.financial_qna import FinancialQnAService
except ImportError:
    print("Could not import app.services.financial_qna")
    sys.exit(1)

# Mock DB to pass __init__
class MockDB:
    def query(self, *args):
        return self
    def filter(self, *args):
        return self
    def first(self):
        # Return a dummy object with base_currency_code if needed
        # But code says: self.user_pref.base_currency_code if self.user_pref else "IDR"
        return None 

def test_parsing():
    db = MockDB()
    service = FinancialQnAService(db, 1)
    
    test_cases = [
        ("tagihan 25 jan - 24 feb 2026", "2026"),
        ("pengeluaran 25 des - 5 jan 2025", "2025"), 
        ("25 januari 2025 sampai 24 februari 2025", "2025"),
    ]
    
    print("Running Verification Tests...")
    
    all_passed = True
    for q, expected_year in test_cases:
        start, end, label = service._parse_period(q)
        print(f"Q: '{q}'")
        print(f"   -> Label: {label}")
        print(f"   -> Start: {start}")
        print(f"   -> End:   {end}")
        
        if label and expected_year in label:
             print("   [PASS] Expected year found in label.")
        else:
             print(f"   [FAIL] Expected year '{expected_year}' NOT found in label.")
             all_passed = False
             
    if all_passed:
        print("\nALL TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    test_parsing()
