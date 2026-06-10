from app.db.session import SessionLocal
from app.db.models import Transaction, TransactionKeyword
from sqlalchemy import or_

# Data provided by user (same list)
UPDATE_DATA = [
    ("#beli es goodday dan gorangan 7k", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli somay 5k", "KONSUMSI"),
    ("#beli cireng 15k", "KONSUMSI"),
    ("#beli es batu 1k", "KONSUMSI"),
    ("#beli ketoprak 15k", "KONSUMSI"),
    ("#bayar wifi bapak 100k", "INTERNET"),
    ("#beli batagor 7k", "KONSUMSI"),
    ("#beli siomay 5k", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli kopi item 3k", "KONSUMSI"),
    ("#bayar laundry 48k", "RUMAH TANGGA"),
    ("#beli galon 20k", "RUMAH TANGGA"),
    ("#beli roko super 25k", "ROKOK"),
    ("#beli makroni 10k", "KONSUMSI"),
    ("#beli gooday 4k", "KONSUMSI"),
    ("#beli saos 5k", "RUMAH TANGGA"),
    ("#beli ciken 8k", "RUMAH TANGGA"),
    ("#beli keredok 13k", "RUMAH TANGGA"),
    ("#beli kopi 8k", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli cemilan 10k", "KONSUMSI"),
    ("#beli pecel ayam 27k", "RUMAH TANGGA"),
    ("#beli pop ice 20k", "KONSUMSI"),
    ("#beli cireng 7500", "KONSUMSI"),
    ("#beli es goodday 10k", "KONSUMSI"),
    ("#beli parfum 20k", "BEAUTY & PERSONAL CARE"),
    ("#beli kacang 2k", "KONSUMSI"),
    ("#beli kopi item 3k", "KONSUMSI"),
    ("#beli nabati 4k", "KONSUMSI"),
    ("#beli batagor 7k", "KONSUMSI"),
    ("#beli siomay 5k", "KONSUMSI"),
    ("#beli roko super 25k", "ROKOK"),
    ("#beli pecel ayam 20k", "RUMAH TANGGA"),
    ("#beli kopi item 3k", "KONSUMSI"),
    ("#beli cireng 5k", "KONSUMSI"),
    ("#beli bakso 17k", "KONSUMSI"),
    ("#beli batu es 2k", "KONSUMSI"),
    ("#bayar parkir 2k", "TRANSPORT"),
    ("#beli donat 10k", "KONSUMSI"),
    ("#beli goodday 5k", "KONSUMSI"),
    ("#beli rokok 25", "ROKOK"),
    ("#beli es luwak 5k", "KONSUMSI"),
    ("#beli nasi padang 12k", "RUMAH TANGGA"),
    ("#beli susu gavin 69700", "CHILDCARE"),
    ("#bayar parkir 2k", "TRANSPORT"),
    ("#beli indome 18k", "RUMAH TANGGA"),
    ("#beli telor 15k", "RUMAH TANGGA"),
    ("#beli es 2k", "KONSUMSI"),
    ("#beli mie 10k", "KONSUMSI"),
    ("#beli gorengan 2k", "KONSUMSI"),
    ("#beli goodday 4k", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli donat 10k", "KONSUMSI"),
    ("#beli nasi padang 20k", "RUMAH TANGGA"),
    ("#beli tehbotol 5k", "KONSUMSI"),
    ("#beli kopi 8k", "KONSUMSI"),
    ("#beli nasgor 15k", "RUMAH TANGGA"),
    ("#beli bensin 30k", "TRANSPORT"),
    ("#beli kopi item 3k", "KONSUMSI"),
    ("#beli cemilan 5k", "KONSUMSI"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli mie 10k", "KONSUMSI"),
    ("#beli esgoodday dan goreng tempe 6k", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli donat 8k", "KONSUMSI"),
    ("#beli nasi padang 12k", "KONSUMSI"),
    ("#beli pecel ayam 16k", "RUMAH TANGGA"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli es teajus 1k", "KONSUMSI"),
    ("#beli ketoprak 13k", "RUMAH TANGGA"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli bengbeng 5k", "KONSUMSI"),
    ("#beli roko 26k", "ROKOK"),
    ("#beli roti 10k", "RUMAH TANGGA"),
    ("#beli pecel ayam 21k", "RUMAH TANGGA"),
    ("#sedekah abang ojol 5k", "DONASI"),
    ("#beli ketupat sayur 10k", "RUMAH TANGGA"),
    ("#beli goodday freeze 5k", "KONSUMSI"),
    ("#beli kopi luwak 3000", "KONSUMSI"),
    ("#beli mie gacoan 40k", "KONSUMSI"),
    ("#beli kopi item 3k", "KONSUMSI"),
    ("#beli bensin 12k", "TRANSPORT"),
    ("#beli roko super 25k", "ROKOK"),
    ("#beli cemilan dan kopi 10k", "KONSUMSI"),
    ("#beli tahu 10k", "RUMAH TANGGA"),
    ("#bayar tagihan 656557", "HUTANG"),
    ("#beli kue 5k", "KONSUMSI"),
    ("#beli lauk 24k", "RUMAH TANGGA"),
    ("#beli roko super 25k", "ROKOK"),
    ("#beli galon 25k", "RUMAH TANGGA"),
    ("#beli esgoodday 5000", "KONSUMSI"),
    ("#beli token 203000", "RUMAH TANGGA"),
    ("#beli laundry 48k", "RUMAH TANGGA"),
    ("#beli sabun 15k", "RUMAH TANGGA"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli donat 6k", "KONSUMSI"),
    ("#beli lauk 18k", "RUMAH TANGGA"),
    ("#beli esgoodday 5k", "KONSUMSI"),
    ("#beli jajan 5k", "KONSUMSI"),
    ("#beli pop ice 10k", "KONSUMSI"),
    ("#beli es goodday freeze 5k", "KONSUMSI"),
    ("#beli bensin 12k", "TRANSPORT"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli risol 6000", "KONSUMSI"),
    ("#beli nabati 4000", "KONSUMSI"),
    ("#beli rokok 25k", "ROKOK"),
    ("#beli telor 15.500", "RUMAH TANGGA"),
    ("#beli lauk 20k", "RUMAH_TANGGA"),
    ("#sedekah sunatan anak dani 100000", "DONASI"),
    ("#beli sosis bakar 10k", "KONSUMSI"),
    ("#beli es mambo 7k", "KONSUMSI"),
    ("#beli sate 10k", "RUMAH TANGGA"),
    ("#beli es goodday 5000", "KONSUMSI"),
    ("#beli rokok 25.500", "ROKOK"),
    ("#beli sabun botol susu 33.500", "CHILDCARE"),
    ("#beli donat 4k", "KONSUMSI"),
    ("#beli lauk 22k", "RUMAH TANGGA"),
    ("#beli bensin 12k", "TRANSPORT"),
    ("#beli es goodday 3k", "KONSUMSI"),
    ("#beli es goodday 5k", "KONSUMSI"),
    ("#beli mie goreng 10k", "RUMAH TANGGA"),
    ("#beli kopi familymart 22000", "KONSUMSI"),
    ("#beli es goodday 5000", "KONSUMSI"),
    ("#beli kue 2500", "KONSUMSI"),
    ("#beli goodday 4000", "KONSUMSI"),
    ("#beli saos 3000", "RUMAH TANGGA"),
    ("#beli donat 6000", "KONSUMSI"),
    ("#beli aqua galon 20k", "RUMAH TANGGA"),
    ("#beli roko super 25k", "ROKOK"),
    ("#beli marimas 8000", "KONSUMSI"),
    ("#beli kerupuk 5000", "RUMAH TANGGA"),
    ("beli kopi Family mart KSK reguler 20500", "KONSUMSI"),
    ("#beli donat 10000", "KONSUMSI"),
    ("#beli bensin 12000", "TRANSPORT"),
    ("beli roko super 25k", "ROKOK"),
    ("beli godday 5k", "KONSUMSI"),
    ("#beli lauk 22000", "RUMAH TANGGA"),
    ("beli lauk 22000", "RUMAH_TANGGA"),
    ("pemasukan 1583561", "GAJI"),
    ("pemasukan 705000", "GAJI")
]

def check_coverage():
    db = SessionLocal()
    keywords = db.query(TransactionKeyword).filter(TransactionKeyword.is_active == True).all()
    # Create map: keyword_lower -> category
    keyword_map = {k.keyword.lower(): k.category for k in keywords}
    
    covered_count = 0
    missing_items = []
    
    print("-" * 50)
    print("Checking Keyword Coverage...")
    print("-" * 50)

    for raw, target_cat in UPDATE_DATA:
        text_lower = raw.lower()
        
        # Check if any existing keyword matches this text
        matched_kw = None
        matched_cat = None
        
        for kw, cat in keyword_map.items():
            if kw in text_lower:
                matched_kw = kw
                matched_cat = cat
                break # Found a match
        
        if matched_kw:
            # Check if category matches
            if matched_cat == target_cat:
                covered_count += 1
            else:
                # Matched but different category
                # print(f"MISMATCH: '{raw}' matched '{matched_kw}'->'{matched_cat}', wanted '{target_cat}'")
                missing_items.append({
                    "raw": raw,
                    "target": target_cat,
                    "reason": f"Mismatch (Found '{matched_kw}' -> '{matched_cat}')"
                })
        else:
            # No keyword match found
            # print(f"MISSING: '{raw}' wanted '{target_cat}'")
            missing_items.append({
                "raw": raw,
                "target": target_cat,
                "reason": "No keyword match"
            })
            
    print(f"\nTotal Items: {len(UPDATE_DATA)}")
    print(f"Covered: {covered_count}")
    print(f"Missing/Mismatch: {len(missing_items)}")
    
    # Suggest new keywords
    print("\nSUGGESTED ACTIONS:")
    suggested_map = {} # keyword -> category
    
    for item in missing_items:
        raw = item['raw'].replace("#", "").lower()
        # Simple extraction: take "beli [word]" or "bayar [word]" or just the first significant word
        # This is a heuristic for suggestion
        parts = raw.split()
        candidate = ""
        
        if "beli" in parts:
            idx = parts.index("beli")
            if idx + 1 < len(parts):
                candidate = parts[idx+1]
                # If next word is 'es', 'kopi', 'nasi', maybe take 2 words?
                if candidate in ['es', 'kopi', 'nasi', 'pecel', 'mie'] and idx + 2 < len(parts):
                     candidate = f"{candidate} {parts[idx+2]}"
        elif "bayar" in parts:
             idx = parts.index("bayar")
             if idx + 1 < len(parts):
                candidate = parts[idx+1]
        elif "pemasukan" in parts:
             candidate = "pemasukan"
        elif "sedekah" in parts:
             candidate = "sedekah"
        else:
            # fallback
            candidate = parts[0] if parts else ""
            
        # Clean up candidate
        candidate = candidate.strip()
        
        if candidate and len(candidate) > 2 and not candidate.isnumeric():
            if candidate not in keyword_map: # Only if not already existing
                if candidate not in suggested_map:
                    suggested_map[candidate] = item['target']
    
    print(f"Found {len(suggested_map)} potential new keywords to add:")
    for k, v in suggested_map.items():
        print(f"  - '{k}' -> '{v}'")

if __name__ == "__main__":
    check_coverage()
