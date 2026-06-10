#!/usr/bin/env python3
"""
Fetch daily gold price (spot XAU/USD → IDR/gram) and save to database.
Runs inside docker container: docker exec finance_web python3 /app/scripts/update_gold_price.py
"""
import json
import urllib.request
import os
import sys

# Database connection
DB_CMD = "psql -U finance_user -d finance_db -c"

def fetch_gold_price_idr():
    """Fetch gold spot price & convert to IDR per gram"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Gold spot in USD/oz
    req = urllib.request.Request('https://api.gold-api.com/price/XAU', headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    gold = json.loads(resp.read().decode())
    price_usd = gold['price']
    
    # USD/IDR exchange rate
    req2 = urllib.request.Request('https://api.exchangerate-api.com/v4/latest/USD', headers=headers)
    resp2 = urllib.request.urlopen(req2, timeout=15)
    fx = json.loads(resp2.read().decode())
    usd_to_idr = fx['rates']['IDR']
    
    # Convert: per gram IDR
    oz_to_gram = 31.1034768
    price_gram_idr = int((price_usd / oz_to_gram) * usd_to_idr)
    
    return price_gram_idr, price_usd, usd_to_idr

if __name__ == '__main__':
    try:
        price_gram, price_usd, rate = fetch_gold_price_idr()
        
        # Save to database via psql
        insert_sql = f"INSERT INTO gold_prices (price_per_gram, source, created_at) VALUES ({price_gram}, 'gold-api.com', NOW());"
        result = os.system(f"docker exec finance_db psql -U finance_user -d finance_db -c \"{insert_sql}\"")
        
        if result == 0:
            print(f"✅ Gold price updated: Rp {price_gram:,}/gram | USD {price_usd:.2f}/oz | Rate: {rate}")
        else:
            print(f"❌ DB insert failed with code {result}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)
