#!/usr/bin/env python3
"""Fetch daily gold price & exchange rates, save to database"""
import json
import urllib.request
import sys
sys.path.insert(0, '/app')
from app.db.session import SessionLocal
from sqlalchemy import text

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Gold spot USD/oz
    req = urllib.request.Request('https://api.gold-api.com/price/XAU', headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    gold = json.loads(resp.read().decode())
    price_usd = gold['price']
    
    # Exchange rates
    req2 = urllib.request.Request('https://api.exchangerate-api.com/v4/latest/USD', headers=headers)
    resp2 = urllib.request.urlopen(req2, timeout=15)
    fx = json.loads(resp2.read().decode())
    usd_to_idr = fx['rates']['IDR']
    gbp_to_idr = fx['rates']['GBP'] * fx['rates']['IDR'] if 'GBP' in fx['rates'] else 0
    
    # Convert gold to IDR/gram
    oz_to_gram = 31.1034768
    price_gram_idr = int((price_usd / oz_to_gram) * usd_to_idr)
    
    return price_gram_idr, price_usd, usd_to_idr, gbp_to_idr

if __name__ == '__main__':
    try:
        price_gram, price_usd, usd_idr, gbp_idr = fetch_data()
        db = SessionLocal()
        db.execute(
            text('''
                INSERT INTO gold_prices (price_per_gram, source, usd_to_idr, gbp_to_idr, created_at) 
                VALUES (:price, :source, :usd, :gbp, NOW())
            '''),
            {'price': price_gram, 'source': 'gold-api.com', 'usd': usd_idr, 'gbp': gbp_idr}
        )
        db.commit()
        db.close()
        print(f'OK|Gold: {price_gram}|USD: {usd_idr}|GBP: {gbp_idr}')
    except Exception as e:
        print(f'FAIL|{e}')
        sys.exit(1)
