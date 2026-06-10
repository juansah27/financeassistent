-- 1. Create AccountType Enum
DO $$ BEGIN
    CREATE TYPE accounttype AS ENUM ('BANK', 'EWALLET', 'CASH', 'INVESTMENT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Add TRANSFER to TransactionType
ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'TRANSFER';

-- 3. Create accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    type accounttype NOT NULL,
    balance NUMERIC(15,2) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_account_user_id ON accounts(user_id);

-- 4. Update transactions table
ALTER TABLE transactions 
    ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id),
    ADD COLUMN IF NOT EXISTS destination_account_id INTEGER REFERENCES accounts(id),
    ADD COLUMN IF NOT EXISTS tags VARCHAR;

-- 5. Update user_preferences table
ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Jakarta';
