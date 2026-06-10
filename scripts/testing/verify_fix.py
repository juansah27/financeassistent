import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.services.financial_qna import FinancialQnAService
except ImportError:
    # If app is not found, we might need to adjust path or we can't run this test easily without proper env
    print("Could not import app.services.financial_qna")
    sys.exit(1)

def test_parsing():
    # We need a dummy db and user_id to instantiate, but _parse_period doesn't use them.
    # So we can pass None.
    service = FinancialQnAService(None, 1)
    
    test_cases = [
        ("tagihan 25 jan - 24 feb 2026", "2026"),
        ("pengeluaran 25 des - 5 jan", "2025"), # Assuming current year is 2026, Dec should be 2025? Wait, depends on logic.
        ("25 januari 2025 sampai 24 februari 2025", "2025"),
    ]
    
    print("Running Verification Tests...")
    
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

if __name__ == "__main__":
    test_parsing()
