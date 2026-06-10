import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration_phase3")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://finance_user:finance_pass@db:5432/finance_db")

def apply_migration():
    engine = create_engine(DATABASE_URL)
    
    # SQL commands to run
    commands = [
        # 1. TRANSACTIONS
        "ALTER TABLE transactions ALTER COLUMN amount TYPE NUMERIC(15,2);",
        "ALTER TABLE transactions ALTER COLUMN amount_in_base_currency TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_transactions_is_deleted ON transactions(is_deleted);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_user_created ON transactions(user_id, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_user_type_created ON transactions(user_id, type, created_at);",
        
        # 2. BUDGETS
        "ALTER TABLE budgets ALTER COLUMN amount TYPE NUMERIC(15,2);",
        "ALTER TABLE budgets ALTER COLUMN percentage TYPE NUMERIC(5,2);",
        "CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON budgets(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_budget_user_period ON budgets(user_id, year, month);",
        
        # 3. RECURRING
        "ALTER TABLE recurring_income ALTER COLUMN amount TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_recurring_income_user_id ON recurring_income(user_id);",
        
        "ALTER TABLE recurring_transactions ALTER COLUMN amount TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_recurring_transactions_user_id ON recurring_transactions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_recurring_transactions_next_due ON recurring_transactions(next_due_date);",
        "CREATE INDEX IF NOT EXISTS idx_recurring_transactions_is_active ON recurring_transactions(is_active);",
        
        # 4. DEBT
        "ALTER TABLE debts ALTER COLUMN total_amount TYPE NUMERIC(15,2);",
        "ALTER TABLE debts ALTER COLUMN remaining_amount TYPE NUMERIC(15,2);",
        "ALTER TABLE debts ALTER COLUMN interest_rate TYPE NUMERIC(5,2);",
        "ALTER TABLE debts ALTER COLUMN installment_amount TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_debts_user_id ON debts(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_debts_is_active ON debts(is_active);",
        
        "ALTER TABLE debt_payments ALTER COLUMN amount TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_debt_payments_debt_id ON debt_payments(debt_id);",
        "CREATE INDEX IF NOT EXISTS idx_debt_payments_tx_id ON debt_payments(transaction_id);",
        
        # 5. ASSETS & GOALS
        "ALTER TABLE assets ALTER COLUMN current_value TYPE NUMERIC(18,2);",
        "ALTER TABLE assets ALTER COLUMN acquisition_value TYPE NUMERIC(18,2);",
        "ALTER TABLE assets ALTER COLUMN quantity TYPE NUMERIC(18,4);",
        "CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);",
        "CREATE INDEX IF NOT EXISTS idx_assets_is_active ON assets(is_active);",
        
        "ALTER TABLE goals ALTER COLUMN target_amount TYPE NUMERIC(15,2);",
        "ALTER TABLE goals ALTER COLUMN current_amount TYPE NUMERIC(15,2);",
        "CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_goals_is_achieved ON goals(is_achieved);",
        
        # 6. MISC
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(user_id, is_read);",
        "CREATE INDEX IF NOT EXISTS idx_receipt_ocr_tx_id ON receipt_ocr(transaction_id);",
        "ALTER TABLE receipt_ocr ALTER COLUMN total_amount TYPE NUMERIC(15,2);",
        "ALTER TABLE currencies ALTER COLUMN exchange_rate_to_base TYPE NUMERIC(18,6);"
    ]
    
    with engine.connect() as conn:
        for cmd in commands:
            try:
                logger.info(f"Executing: {cmd}")
                conn.execute(text(cmd))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to execute command: {cmd}\nError: {e}")
                conn.rollback()
    
    logger.info("Migration Phase 3 completed!")

if __name__ == "__main__":
    apply_migration()
