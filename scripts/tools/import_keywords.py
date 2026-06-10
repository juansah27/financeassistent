from app.db.session import SessionLocal
from app.db.models import TransactionKeyword
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Suggested keywords from coverage check
SUGGESTED_KEYWORDS = [
  ('es goodday', 'KONSUMSI'),
  ('rokok', 'ROKOK'),
  ('somay', 'KONSUMSI'),
  ('cireng', 'KONSUMSI'),
  ('es batu', 'KONSUMSI'),
  ('ketoprak', 'KONSUMSI'),
  ('wifi', 'INTERNET'),
  ('batagor', 'KONSUMSI'),
  ('siomay', 'KONSUMSI'),
  ('kopi item', 'KONSUMSI'),
  ('galon', 'RUMAH TANGGA'),
  ('roko', 'ROKOK'),
  ('makroni', 'KONSUMSI'),
  ('gooday', 'KONSUMSI'),
  ('saos', 'RUMAH TANGGA'),
  ('ciken', 'RUMAH TANGGA'),
  ('keredok', 'RUMAH TANGGA'),
  ('kopi 8k', 'KONSUMSI'),
  ('cemilan', 'KONSUMSI'),
  ('pecel ayam', 'RUMAH TANGGA'),
  ('pop', 'KONSUMSI'),
  ('parfum', 'BEAUTY & PERSONAL CARE'),
  ('kacang', 'KONSUMSI'),
  ('nabati', 'KONSUMSI'),
  ('bakso', 'KONSUMSI'),
  ('batu', 'KONSUMSI'),
  ('parkir', 'TRANSPORT'),
  ('donat', 'KONSUMSI'),
  ('goodday', 'KONSUMSI'),
  ('es luwak', 'KONSUMSI'),
  ('nasi padang', 'RUMAH TANGGA'),
  ('susu', 'CHILDCARE'),
  ('indome', 'RUMAH TANGGA'),
  ('telor', 'RUMAH TANGGA'),
  ('es 2k', 'KONSUMSI'),
  ('mie 10k', 'KONSUMSI'),
  ('gorengan', 'KONSUMSI'),
  ('tehbotol', 'KONSUMSI'),
  ('nasgor', 'RUMAH TANGGA'),
  ('esgoodday', 'KONSUMSI'),
  ('es teajus', 'KONSUMSI'),
  ('bengbeng', 'KONSUMSI'),
  ('roti', 'RUMAH TANGGA'),
  ('ketupat', 'RUMAH TANGGA'),
  ('kopi luwak', 'KONSUMSI'),
  ('mie gacoan', 'KONSUMSI'),
  ('tahu', 'RUMAH TANGGA'),
  ('kue', 'KONSUMSI'),
  ('lauk', 'RUMAH TANGGA'),
  ('token', 'RUMAH TANGGA'),
  ('sabun', 'RUMAH TANGGA'),
  ('jajan', 'KONSUMSI'),
  ('risol', 'KONSUMSI'),
  ('sosis', 'KONSUMSI'),
  ('es mambo', 'KONSUMSI'),
  ('sate', 'RUMAH TANGGA'),
  ('mie goreng', 'RUMAH TANGGA'),
  ('kopi familymart', 'KONSUMSI'),
  ('aqua', 'RUMAH TANGGA'),
  ('marimas', 'KONSUMSI'),
  ('kerupuk', 'RUMAH TANGGA'),
  ('kopi family', 'KONSUMSI'),
  ('godday', 'KONSUMSI')
]

def import_keywords():
    db = SessionLocal()
    added_count = 0
    skipped_count = 0
    
    print(f"Starting import for {len(SUGGESTED_KEYWORDS)} keywords...")
    
    try:
        for kw, category in SUGGESTED_KEYWORDS:
            # Check if exists
            existing = db.query(TransactionKeyword).filter(TransactionKeyword.keyword == kw).first()
            
            if existing:
                if existing.category != category:
                    existing.category = category
                    logger.info(f"Updated category for '{kw}': -> {category}")
                    added_count += 1
                else:
                    skipped_count += 1
            else:
                new_kw = TransactionKeyword(
                    keyword=kw,
                    category=category,
                    is_active=True
                )
                db.add(new_kw)
                logger.info(f"Added new keyword: '{kw}' -> {category}")
                added_count += 1
                
        db.commit()
    except Exception as e:
        logger.error(f"Error importing keywords: {e}")
        db.rollback()
    finally:
        db.close()

    print("\nImport Summary:")
    print(f"Total Processed: {len(SUGGESTED_KEYWORDS)}")
    print(f"Added/Updated: {added_count}")
    print(f"Skipped (Already exists): {skipped_count}")

if __name__ == "__main__":
    import_keywords()
