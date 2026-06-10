
import re

text = """m-Transfer:
BERHASIL
25/01/2026 14:04:41
1260895330565959
SHOPEE
SXXXXXX2
TOTAL TAGIHAN Rp. 107,600.00
Kirim ke sella"""

text_upper = text.upper()

amount_patterns = [
    r'(?:TOTAL|JUMLAH|TOTAL\s+TAGIHAN|TRANSFER|BERHASIL)[\s:]*Rp?\s*([\d.,]+)',
    r'Rp\s*([\d.,]+)',
    r'([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)',
]

print(f"Testing text: {text_upper}")

for i, pattern in enumerate(amount_patterns):
    print(f"\nPattern {i+1}: {pattern}")
    matches = re.findall(pattern, text_upper, re.IGNORECASE)
    print(f"Matches: {matches}")
    if matches:
        for match in matches:
            clean_num = match.replace('.', '').replace(',', '')
            print(f"  Match: '{match}' -> Clean: '{clean_num}'")
            try:
                val = int(clean_num)
                print(f"  Int Value: {val}")
            except:
                print("  Invalid int")
