import sys
import os
import re
from datetime import datetime, timedelta

# Mocking the Service logic locally to test _parse_period
def parse_period(question: str):
    now = datetime.now()
    
    month_map = {
        "januari": 1, "jan": 1, "january": 1, "februari": 2, "feb": 2, "february": 2, 
        "maret": 3, "mar": 3, "march": 3, "april": 4, "apr": 4, 
        "mei": 5, "may": 5, "juni": 6, "jun": 6, "june": 6,
        "juli": 7, "jul": 7, "july": 7, "agustus": 8, "aug": 8, "august": 8, 
        "september": 9, "sep": 9, "sept": 9, "oktober": 10, "okt": 10, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "desember": 12, "des": 12, "dec": 12, "december": 12
    }
    
    # CURRENT LOGIC (from app/services/financial_qna.py)
    date_pattern = r"(\d{1,2})\s+([a-zA-Z]+)"
    
    # Look for "sampai" or "-" with dates
    range_match = re.search(f"{date_pattern}.*?(?:sampai|-).*?{date_pattern}", question)
    
    if range_match:
        try:
            # The current logic only captures 4 groups: d1, m1, d2, m2
            print(f"DEBUG: Groups found: {range_match.groups()}")
            d1, m1_str, d2, m2_str = range_match.groups()
            m1 = month_map.get(m1_str.lower())
            m2 = month_map.get(m2_str.lower())
            
            if m1 and m2:
                y = now.year
                start_date = datetime(y, m1, int(d1))
                end_date = datetime(y, m2, int(d2))
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
                label = f"{d1} {m1_str.capitalize()} - {d2} {m2_str.capitalize()} {y}"
                return start_date, end_date, label
        except Exception as e:
            print(f"DEBUG: Exception: {e}")
            pass

    return None, None, None

def test():
    q = "tagihan 25 januari - 24 februari 2026"
    print(f"Testing Question: '{q}'")
    start, end, label = parse_period(q)
    
    print(f"Result: Label={label}, Start={start}, End={end}")
    
    if label and "2026" in label:
         print("SUCCESS: 2026 detected")
    else:
         print("FAIL: 2026 NOT detected correctly (likely used current year)")

if __name__ == "__main__":
    test()
