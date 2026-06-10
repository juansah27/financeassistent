# Finance DB Knowledge

## Database Connection
- **Container:** `finance_db` (PostgreSQL 15)
- **Credentials:** user `finance_user`, password `finance_pass`, database `finance_db`
- **Query command:**
```bash
docker exec finance_db psql -U finance_user -d finance_db -c "SQL_HERE"
```

## Database Schema Reference

### Enums
- **TransactionType:** INCOME, EXPENSE, SAVING, INVESTMENT, DEBT, TRANSFER (selalu UPPERCASE)
- **AccountType:** BANK, EWALLET, CASH, INVESTMENT
- **DebtType:** PERSONAL, BANK, LEASING, CREDIT_CARD, PAYLATER, BILL
- **AssetType:** BPJS, GOLD, PROPERTY, VEHICLE, DEPOSIT, STOCK, CRYPTO
- **RecurrenceType:** DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM

### Users
- user_id=1: Juansah (whatsapp: 62895330533454)
- user_id=2: Sella (whatsapp: 62895330565959)

### Core Tables
- **transactions** — ledger utama: user_id, type, amount, category, description, account_id, created_at, is_deleted, tags, notes
- **accounts** — dompet/rekening: user_id, name, type, balance, is_active
- **budgets** — budget per bulan: user_id, category, amount, year, month
- **debts** — hutang: user_id, type, creditor, total_amount, remaining_amount, installment_amount
- **debt_payments** — riwayat bayar hutang: debt_id, transaction_id, amount, payment_date
- **assets** — aset: user_id, asset_type, name, current_value, quantity, unit
- **asset_history** — histori aset: asset_id, old_value, new_value
- **recurring_transactions** — transaksi berulang: user_id, type, amount, category, recurrence_type, day_of_month, next_due_date, is_active
- **recurring_income** — pendapatan bulanan: user_id, name, amount, category, status
- **go