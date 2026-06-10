from app.db import session, models
import sys

def sync_transactions():
    print("⏳ Starting transaction synchronization...")
    db = session.SessionLocal()
    try:
        # 1. Load active keywords map
        # Retrieve all active keywords that have a category assigned
        keywords = db.query(models.TransactionKeyword).filter(
            models.TransactionKeyword.is_active == True,
            models.TransactionKeyword.category != None
        ).all()
        
        # Sort by length desc to match longest keyword first (e.g. "uber eats" before "uber")
        keywords.sort(key=lambda x: len(x.keyword), reverse=True)
        
        print(f"📋 Loaded {len(keywords)} active keywords for matching.")

        # 2. Get all transactions
        transactions = db.query(models.Transaction).all()
        print(f"🔍 Scanning {len(transactions)} transactions...")
        
        updated_count = 0
        
        for t in transactions:
            # text to match: combining raw_input and description for better coverage
            # usually description is the clean one, but raw_input might have details
            text_sources = []
            if t.description: text_sources.append(t.description.lower())
            if t.raw_input: text_sources.append(t.raw_input.lower())
            
            text = " ".join(text_sources)
            
            if not text:
                continue
                
            original_category = t.category
            
            matched_category = None
            matched_kw = None
            
            # Find first matching keyword
            for k in keywords:
                if k.keyword.lower() in text:
                    matched_category = k.category
                    matched_kw = k.keyword
                    break 
            
            # If match found and category is different, update it
            if matched_category and matched_category != original_category:
                t.category = matched_category
                updated_count += 1
                print(f"   ✏️ Info: ID {t.id} [{text[:30]}...] : '{original_category}' ➔ '{matched_category}' (matched '{matched_kw}')")
        
        if updated_count > 0:
            db.commit()
            print(f"\n✅ SUCCESS! Updated {updated_count} transactions.")
        else:
            print("\n✅ verification complete. No changes needed.")
            
    except Exception as e:
        print(f"\n❌ Error during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_transactions()
