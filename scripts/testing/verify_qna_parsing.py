import sys
import os
from datetime import datetime

# Mocking the Service to test _detect_intent and _parse_period without DB
class MockService:
    def _parse_period(self, question: str):
        """
        Copied from FinancialQnAService._parse_period for testing logic
        """
        import re
        from datetime import datetime, timedelta
        
        # Mock 'now' to be consistent for tests
        # Let's assume 'now' is 2025-02-10 for testing purposes
        # But since the code uses datetime.now(), we might get dynamic results.
        # For this test, we will let it use actual system time but verify relative deltas or dates.
        now = datetime.now()
        
        month_map = {
            "januari": 1, "jan": 1, "january": 1, "februari": 2, "feb": 2, "february": 2, 
            "maret": 3, "mar": 3, "march": 3, "april": 4, "apr": 4, 
            "mei": 5, "may": 5, "juni": 6, "jun": 6, "june": 6,
            "juli": 7, "jul": 7, "july": 7, "agustus": 8, "aug": 8, "august": 8, 
            "september": 9, "sep": 9, "sept": 9, "oktober": 10, "okt": 10, "october": 10, "oct": 10,
            "november": 11, "nov": 11, "desember": 12, "des": 12, "dec": 12, "december": 12
        }
        
        date_pattern = r"(\d{1,2})\s+([a-zA-Z]+)"
        
        # 1. Custom Range
        range_match = re.search(f"{date_pattern}.*?(?:sampai|-).*?{date_pattern}", question)
        
        if range_match:
            try:
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
            except Exception:
                pass

        # 2. Specific Month
        for m_name, m_val in month_map.items():
            if m_name in question:
                year_match = re.search(r"\b20\d{2}\b", question)
                year = int(year_match.group(0)) if year_match else now.year
                
                start_date = datetime(year, m_val, 1)
                if m_val == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    end_date = datetime(year, m_val + 1, 1) - timedelta(seconds=1)
                
                return start_date, end_date, f"{m_name.capitalize()} {year}"

        # 3. Relative periods
        if "bulan lalu" in question:
            first_this_month = now.replace(day=1)
            end_date = first_this_month - timedelta(seconds=1)
            start_date = end_date.replace(day=1)
            return start_date, end_date, "Bulan Lalu"
            
        if "minggu ini" in question:
            start_date = now - timedelta(days=now.weekday()) # Monday
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            return start_date, end_date, "Minggu Ini"

        return None, None, None

service = MockService()

test_cases = [
    "pengeluaran januari",
    "pengeluaran januari 2024",
    "pengeluaran 10 jan sampai 20 jan",
    "pengeluaran bulan lalu",
    "pengeluaran minggu ini",
    "pengeluaran hari ini" # Should be None
]

print("Running Parsing Tests...")
for q in test_cases:
    start, end, label = service._parse_period(q)
    print(f"Q: '{q}' -> Label: {label}, Start: {start}, End: {end}")
