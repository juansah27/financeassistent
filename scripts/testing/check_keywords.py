"""
Check if keyword 'sedekah' exists in database
"""
import sys
sys.path.insert(0, '/app')

from app.db import session
from app.db.models import TransactionKeyword

def main():
    db = next(session.get_db())
    try:
        print("=" * 60)
        print("Checking Keywords in Database")
        print("=" * 60)
        print()
        
        # Check for sedekah keyword
        sedekah_keywords = db.query(TransactionKeyword).filter(
            TransactionKeyword.keyword.ilike('%sedekah%')
        ).all()
        
        if sedekah_keywords:
            print(f"✅ Found {len(sedekah_keywords)} 'sedekah' keyword(s):")
            for kw in sedekah_keywords:
                print(f"  - Keyword: '{kw.keyword}'")
                print(f"    Category: {kw.category.value}")
                print(f"    Type: {kw.type.value}")
                print(f"    User ID: {kw.user_id}")
                print()
        else:
            print("❌ No 'sedekah' keyword found in database")
            print()
        
        # Show all keywords for debugging
        print("All keywords in database:")
        all_keywords = db.query(TransactionKeyword).all()
        print(f"Total: {len(all_keywords)} keywords")
        print()
        
        for kw in all_keywords[:10]:  # Show first 10
            print(f"  - '{kw.keyword}' → {kw.category.value} ({kw.type.value})")
        
        if len(all_keywords) > 10:
            print(f"  ... and {len(all_keywords) - 10} more")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
