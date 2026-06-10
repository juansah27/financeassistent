"""
Migration script to add debt-related tables to the database
Run this script to create the debts and debt_payments tables
"""
import sys
import os

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import engine, Base
from app.db.models import Debt, DebtPayment
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Create debt-related tables"""
    try:
        logger.info("Starting debt tables migration...")
        
        # Create only the new tables (existing tables won't be affected)
        Debt.__table__.create(bind=engine, checkfirst=True)
        DebtPayment.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("✓ Successfully created debt tables:")
        logger.info("  - debts")
        logger.info("  - debt_payments")
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
