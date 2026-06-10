from app.db.session import SessionLocal
from app.db.models import Transaction
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Data provided by user
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

def update_categories():
    db = SessionLocal()
    updated_count = 0
    skips_count = 0
    not_found_count = 0

    print(f"Starting update for {len(UPDATE_DATA)} items...")
    
    try:
        for raw_input, target_category in UPDATE_DATA:
            # Normalize target category (remove underscores for consistency if needed, but user text has spaces)
            # User specifically asked for 'RUMAH_TANGGA' in some, 'RUMAH TANGGA' in others. 
            # I will trust the provided mapping exactly.
            
            # Find transactions with matching raw_input
            transactions = db.query(Transaction).filter(Transaction.raw_input == raw_input).all()
            
            if not transactions:
                # Try adding # prefix if missing in DB but present in raw_input
                if not raw_input.startswith("#"):
                     transactions_alt = db.query(Transaction).filter(Transaction.raw_input == "#" + raw_input).all()
                     if transactions_alt:
                         transactions = transactions_alt
                
                # Try removing # prefix if present in raw_input but missing in DB
                if not transactions and raw_input.startswith("#"):
                     transactions_alt = db.query(Transaction).filter(Transaction.raw_input == raw_input[1:]).all()
                     if transactions_alt:
                         transactions = transactions_alt

            if not transactions:
                # logger.warning(f"Not found: {raw_input}")
                not_found_count += 1
                continue
                
            for txn in transactions:
                if txn.category != target_category:
                    old_cat = txn.category
                    txn.category = target_category
                    updated_count += 1
                    logger.info(f"Updated: '{raw_input}' | {old_cat} -> {target_category}")
                else:
                    skips_count += 1
        
        db.commit()
    except Exception as e:
        logger.error(f"Error during update: {e}")
        db.rollback()
    finally:
        db.close()

    print("\nSummary:")
    print(f"Total processed: {len(UPDATE_DATA)}")
    print(f"Updated: {updated_count}")
    print(f"Skipped (Already correct): {skips_count}")
    print(f"Not Found (No matching transaction): {not_found_count}")

if __name__ == "__main__":
    update_categories()
