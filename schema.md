# Database Schema Reference — Finance Assistant

> **Source of truth:** `app/db/models.py`
> **Database:** PostgreSQL 15 (Alpine) — container `finance_db`
> **Credentials:** user `finance_user`, password `finance_pass`, database `finance_db`

---

## Table of Contents

- [Enums](#enums)
- [Core Tables](#core-tables)
  - [users](#users)
  - [families](#families)
  - [family_members](#family_members)
  - [transactions](#transactions)
  - [budgets](#budgets)
- [Recurring & Scheduling](#recurring--scheduling)
  - [recurring_transactions](#recurring_transactions)
  - [recurring_income](#recurring_income)
  - [pending_confirmations](#pending_confirmations)
- [Debt Management](#debt-management)
  - [debts](#debts)
  - [debt_payments](#debt_payments)
- [Assets](#assets)
  - [assets](#assets-1)
  - [asset_history](#asset_history)
- [Categories & Keywords](#categories--keywords)
  - [transaction_keywords](#transaction_keywords)
  - [user_categories](#user_categories)
- [Media & OCR](#media--ocr)
  - [transaction_photos](#transaction_photos)
  - [receipt_ocr](#receipt_ocr)
- [Audit & History](#audit--history)
  - [transaction_edits](#transaction_edits)
- [Goals](#goals)
- [Notifications](#notifications)
- [Currencies](#currencies)
- [User Preferences](#user_preferences)
- [Bot & WhatsApp](#bot--whatsapp)
  - [bot_reply_templates](#bot_reply_templates)
  - [whatsapp_report_schedules](#whatsapp_report_schedules)
  - [whatsapp_groups](#whatsapp_groups)
- [Indexes Summary](#indexes-summary)
- [Important Notes](#important-notes)

---

## Enums

### TransactionType
```sql
CREATE TYPE transactiontype AS ENUM (
    'INCOME',      -- Pemasukan
    'EXPENSE',     -- Pengeluaran
    'SAVING',      -- Tabungan
    'INVESTMENT',  -- Investasi
    'DEBT',        -- Hutang
    'TRANSFER'     -- Transfer antar rekening
);
```
> **Selalu gunakan UPPERCASE** saat query.

### AccountType
```sql
CREATE TYPE accounttype AS ENUM (
    'BANK',         -- Bank
    'EWALLET',      -- e-Wallet
    'CASH',         -- Uang Tunai
    'INVESTMENT'    -- Rekening Investasi
);
```

### DebtType
```sql
CREATE TYPE debttype AS ENUM (
    'PERSONAL',     -- personal
    'BANK',         -- bank
    'LEASING',      -- leasing
    'CREDIT_CARD',  -- credit_card
    'PAYLATER',     -- paylater
    'BILL'          -- bill
);
```

### RecurrenceType
```sql
CREATE TYPE recurrencetype AS ENUM (
    'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY', 'CUSTOM'
);
```

### RecurringIncomeFrequency
```sql
CREATE TYPE recurringincomefrequency AS ENUM ('MONTHLY');
```

### RecurringIncomeStatus
```sql
CREATE TYPE recurringincomestatus AS ENUM ('ACTIVE', 'INACTIVE');
```

### AssetType
```sql
CREATE TYPE assettype AS ENUM (
    'BPJS',      -- BPJS Ketenagakerjaan
    'GOLD',      -- Emas
    'PROPERTY',  -- Properti
    'VEHICLE',   -- Kendaraan
    'DEPOSIT',   -- Deposito
    'STOCK',     -- Saham/Reksadana
    'CRYPTO'     -- Cryptocurrency
);
```

---

## Core Tables

### users

Menyimpan data pengguna. Terhubung ke keluarga (family) secara opsional.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `username` | VARCHAR | NO | — | UNIQUE, indexed |
| `pin_hash` | VARCHAR | NO | — | Hashed PIN |
| `family_id` | INTEGER | YES | NULL | FK → `families.id` |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

**Known Users:**
- user_id=1, username=`Juansah`, whatsapp `62895330533454`
- user_id=2, username=`Sella`, whatsapp `62895330565959`

---

### families

Mengelompokkan pengguna dalam satu keluarga.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `name` | VARCHAR | NO | — | Nama keluarga |
| `join_code` | VARCHAR(10) | NO | — | UNIQUE, indexed |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

**Relationships:** `users` (one-to-many)

---

### accounts

Tabel penyimpanan uang/dompet pengguna.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `name` | VARCHAR | NO | — | e.g., BCA, GoPay, Dompet Utama |
| `type` | accounttype | NO | — | ENUM |
| `balance` | NUMERIC(15,2) | NO | 0.0 | Saldo terkini |
| `is_active` | BOOLEAN | NO | true | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

### family_members

Anggota keluarga yang terkait dengan transaksi (ayah, ibu, anak, dll).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | Owner, indexed |
| `name` | VARCHAR | NO | — | Nama anggota |
| `role` | VARCHAR | YES | NULL | ayah, ibu, anak, dll |
| `is_active` | BOOLEAN | NO | true | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

### transactions

Tabel utama untuk semua transaksi keuangan.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `type` | transactiontype | NO | — | ENUM, indexed |
| `amount` | NUMERIC(15,2) | NO | — | Selalu positif |
| `category` | VARCHAR | NO | — | indexed |
| `description` | VARCHAR | YES | NULL | Deskripsi ternormalisasi |
| `raw_input` | VARCHAR | YES | NULL | Input asli dari user |
| `created_at` | TIMESTAMPTZ | NO | NOW() | indexed |
| `recurring_id` | INTEGER | YES | NULL | FK → `recurring_transactions.id` |
| `family_member_id` | INTEGER | YES | NULL | FK → `family_members.id` |
| `account_id` | INTEGER | YES | NULL | FK → `accounts.id` (Sumber) |
| `destination_account_id`| INTEGER | YES | NULL | FK → `accounts.id` (Tujuan Transfer) |
| `currency_code` | VARCHAR(3) | NO | 'IDR' | — |
| `amount_in_base_currency` | NUMERIC(15,2) | YES | NULL | Konversi ke mata uang dasar |
| `tags` | VARCHAR | YES | NULL | Comma-separated tags (e.g. #Liburan) |
| `notes` | TEXT | YES | NULL | Catatan tambahan |
| `is_deleted` | BOOLEAN | NO | false | Soft delete, indexed |
| `deleted_at` | TIMESTAMPTZ | YES | NULL | — |

**Relationships:**
- `photos` → `transaction_photos` (one-to-many, cascade delete)
- `recurring` → `recurring_transactions`
- `edits` → `transaction_edits` (cascade delete)
- `ocr_data` → `receipt_ocr` (cascade delete)
- `account` & `destination_account` → `accounts`

**Composite Indexes:**
```sql
CREATE INDEX idx_transaction_user_created ON transactions(user_id, created_at);
CREATE INDEX idx_transaction_user_type_created ON transactions(user_id, type, created_at);
```

> **PENTING:** Selalu set `is_deleted = false` saat INSERT transaksi baru.

---

### budgets

Budget bulanan per kategori.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `category` | VARCHAR | NO | — | — |
| `amount` | NUMERIC(15,2) | NO | — | Jumlah budget |
| `percentage` | NUMERIC(5,2) | YES | NULL | Persentase dari income (0-100) |
| `year` | INTEGER | NO | — | Tahun |
| `month` | INTEGER | NO | — | Bulan (1-12) |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

**Composite Index:**
```sql
CREATE INDEX idx_budget_user_period ON budgets(user_id, year, month);
```

---

## Recurring & Scheduling

### recurring_transactions

Transaksi berulang (tagihan, langganan, pendapatan rutin).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `type` | transactiontype | NO | — | ENUM |
| `amount` | NUMERIC(15,2) | NO | — | — |
| `category` | VARCHAR | NO | — | — |
| `description` | VARCHAR | YES | NULL | — |
| `recurrence_type` | recurrencetype | NO | — | ENUM |
| `day_of_month` | INTEGER | YES | NULL | Untuk monthly (1-31) |
| `interval_days` | INTEGER | YES | NULL | Untuk custom |
| `next_due_date` | TIMESTAMPTZ | NO | — | indexed |
| `is_active` | BOOLEAN | NO | true | indexed |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `remaining_occurrences` | INTEGER | YES | NULL | Sisa pengulangan |
| `last_paid_at` | TIMESTAMPTZ | YES | NULL | — |

**Relationships:** `transactions` (one-to-many)

---

### recurring_income

Pendapatan berulang bulanan (gaji, sewa, passive income).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `name` | VARCHAR(255) | NO | — | e.g. "Gaji Bulanan" |
| `amount` | NUMERIC(15,2) | NO | — | — |
| `category` | VARCHAR | NO | — | — |
| `frequency` | recurringincomefrequency | NO | MONTHLY | ENUM |
| `status` | recurringincomestatus | NO | ACTIVE | ENUM |
| `notes` | TEXT | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

### pending_confirmations

Konfirmasi pending dari user (e.g. update recurring setelah input manual).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `transaction_id` | INTEGER | YES | NULL | Transaksi pemicu |
| `recurring_id` | INTEGER | NO | — | Recurring yang akan diupdate |
| `action_type` | VARCHAR | NO | 'update_recurring' | — |
| `data` | TEXT | YES | NULL | JSON string |
| `expires_at` | TIMESTAMPTZ | NO | — | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Debt Management

### debts

Manajemen hutang (personal, bank, leasing, kartu kredit, paylater).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `type` | debttype | NO | PERSONAL | ENUM |
| `creditor` | VARCHAR | NO | — | Nama kreditur |
| `name` | VARCHAR | YES | NULL | Nama pinjaman |
| `total_amount` | NUMERIC(15,2) | NO | — | Total hutang |
| `remaining_amount` | NUMERIC(15,2) | NO | — | Sisa hutang |
| `interest_rate` | NUMERIC(5,2) | YES | NULL | Bunga (%) |
| `tenor` | INTEGER | YES | NULL | Jangka waktu (bulan) |
| `installment_amount` | NUMERIC(15,2) | YES | NULL | Cicilan per bulan |
| `start_date` | TIMESTAMPTZ | NO | NOW() | — |
| `due_date` | TIMESTAMPTZ | YES | NULL | — |
| `is_active` | BOOLEAN | NO | true | indexed |
| `notes` | TEXT | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

**Relationships:** `payments` → `debt_payments` (one-to-many, cascade delete)

---

### debt_payments

Riwayat pembayaran hutang.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `debt_id` | INTEGER | NO | — | FK → `debts.id`, indexed |
| `transaction_id` | INTEGER | YES | NULL | FK → `transactions.id`, indexed |
| `amount` | NUMERIC(15,2) | NO | — | — |
| `payment_date` | TIMESTAMPTZ | NO | NOW() | — |
| `notes` | TEXT | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Assets

### assets

Pencatatan aset (emas, properti, saham, crypto, dll).

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `asset_type` | assettype | NO | — | ENUM, indexed |
| `name` | VARCHAR | NO | — | — |
| `current_value` | NUMERIC(18,2) | NO | — | Nilai saat ini |
| `acquisition_date` | TIMESTAMPTZ | YES | NULL | Tanggal perolehan |
| `acquisition_value` | NUMERIC(18,2) | YES | NULL | Nilai perolehan |
| `quantity` | NUMERIC(18,4) | YES | NULL | Jumlah (gram, lot, dll) |
| `unit` | VARCHAR(50) | YES | NULL | Satuan |
| `notes` | TEXT | YES | NULL | — |
| `is_active` | BOOLEAN | NO | true | indexed |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

**Relationships:** `history` → `asset_history` (one-to-many, cascade delete)

---

### asset_history

Riwayat perubahan nilai aset.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `asset_id` | INTEGER | NO | — | FK → `assets.id` |
| `old_value` | FLOAT | NO | — | — |
| `new_value` | FLOAT | NO | — | — |
| `updated_by_user_id` | INTEGER | NO | — | — |
| `notes` | TEXT | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Categories & Keywords

### transaction_keywords

Mapping keyword → kategori untuk auto-deteksi.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `keyword` | VARCHAR | NO | — | UNIQUE, indexed, lowercase |
| `category` | VARCHAR | YES | NULL | Kategori tujuan |
| `is_active` | BOOLEAN | NO | true | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

**Urutan lookup kategori:**
1. Inline keywords (hardcoded di parser)
2. Tabel `transaction_keywords` (active only)
3. Tanya user jika tidak dikenali

---

### user_categories

Kategori kustom per user.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `name` | VARCHAR | NO | — | Nama kategori |
| `type` | VARCHAR | NO | — | 'income' atau 'expense' |
| `icon` | VARCHAR | YES | NULL | — |
| `color` | VARCHAR | YES | NULL | Hex color |
| `is_default` | BOOLEAN | NO | false | System defaults |
| `is_active` | BOOLEAN | NO | true | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Media & OCR

### transaction_photos

Foto yang dilampirkan ke transaksi.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `transaction_id` | INTEGER | NO | — | FK → `transactions.id` |
| `filename` | VARCHAR | NO | — | — |
| `file_path` | VARCHAR | NO | — | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

### receipt_ocr

Hasil OCR dari foto struk/receipt.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `transaction_id` | INTEGER | NO | — | FK → `transactions.id`, indexed |
| `photo_id` | INTEGER | NO | — | FK → `transaction_photos.id` |
| `extracted_text` | TEXT | YES | NULL | Teks hasil ekstraksi |
| `merchant_name` | VARCHAR | YES | NULL | — |
| `total_amount` | NUMERIC(15,2) | YES | NULL | — |
| `date_detected` | TIMESTAMPTZ | YES | NULL | — |
| `items` | TEXT | YES | NULL | JSON string of items |
| `confidence_score` | FLOAT | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Audit & History

### transaction_edits

Riwayat perubahan transaksi.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `transaction_id` | INTEGER | NO | — | FK → `transactions.id` |
| `edited_by_user_id` | INTEGER | NO | — | — |
| `old_amount` | FLOAT | YES | NULL | — |
| `new_amount` | FLOAT | YES | NULL | — |
| `old_category` | VARCHAR | YES | NULL | — |
| `new_category` | VARCHAR | YES | NULL | — |
| `old_description` | VARCHAR | YES | NULL | — |
| `new_description` | VARCHAR | YES | NULL | — |
| `edit_reason` | VARCHAR | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Goals

### goals

Target keuangan pengguna.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | indexed |
| `name` | VARCHAR | NO | — | — |
| `target_amount` | NUMERIC(15,2) | NO | — | — |
| `current_amount` | NUMERIC(15,2) | NO | 0.0 | — |
| `target_date` | TIMESTAMPTZ | YES | NULL | — |
| `is_achieved` | BOOLEAN | NO | false | indexed |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

## Notifications

### notifications

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | — |
| `title` | VARCHAR | NO | — | — |
| `message` | TEXT | NO | — | — |
| `notification_type` | VARCHAR | NO | — | budget / recurring / goal / reminder |
| `is_read` | BOOLEAN | NO | false | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Currencies

### currencies

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `code` | VARCHAR(3) | NO | — | UNIQUE (USD, IDR, etc) |
| `name` | VARCHAR | NO | — | — |
| `symbol` | VARCHAR | NO | — | — |
| `exchange_rate_to_base` | NUMERIC(18,6) | NO | 1.0 | Rate ke IDR |
| `is_base` | BOOLEAN | NO | false | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

## User Preferences

### user_preferences

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | UNIQUE |
| `dark_mode` | BOOLEAN | NO | false | — |
| `base_currency_code` | VARCHAR(3) | NO | 'IDR' | — |
| `language` | VARCHAR(10) | NO | 'id' | — |
| `timezone` | VARCHAR(50) | NO | 'Asia/Jakarta' | — |
| `start_of_month` | INTEGER | NO | 1 | Hari reset budget (1-28) |
| `date_format` | VARCHAR(20) | NO | 'DD/MM/YYYY' | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

## Bot & WhatsApp

### bot_reply_templates

Template balasan bot dengan placeholder.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `name` | VARCHAR | NO | — | default / success / error |
| `template` | TEXT | NO | — | Placeholder: `{transaction_id}`, `{amount}`, `{category}`, `{type}` |
| `is_active` | BOOLEAN | NO | true | — |
| `is_default` | BOOLEAN | NO | false | Hanya satu yang boleh default |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

### whatsapp_report_schedules

Jadwal laporan otomatis via WhatsApp.

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `user_id` | INTEGER | NO | — | — |
| `is_enabled` | BOOLEAN | NO | true | — |
| `report_time` | VARCHAR(5) | NO | '10:00' | Format "HH:MM" |
| `group_name` | VARCHAR | YES | NULL | — |
| `group_id` | VARCHAR | YES | NULL | — |
| `last_sent_at` | TIMESTAMPTZ | YES | NULL | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |
| `updated_at` | TIMESTAMPTZ | YES | NULL | — |

---

### whatsapp_groups

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | SERIAL | NO | auto | PK |
| `group_id` | VARCHAR | NO | — | UNIQUE, indexed |
| `name` | VARCHAR | NO | — | — |
| `last_active_at` | TIMESTAMPTZ | NO | NOW() | Auto-update |
| `is_allowed` | BOOLEAN | NO | true | — |
| `created_at` | TIMESTAMPTZ | NO | NOW() | — |

---

## Indexes Summary

```sql
-- transactions
CREATE INDEX idx_transaction_user_created ON transactions(user_id, created_at);
CREATE INDEX idx_transaction_user_type_created ON transactions(user_id, type, created_at);
-- Also auto-indexed: id, user_id, type, category, created_at, is_deleted

-- budgets
CREATE INDEX idx_budget_user_period ON budgets(user_id, year, month);

-- transaction_keywords
CREATE UNIQUE INDEX ON transaction_keywords(keyword);

-- recurring_transactions (auto-indexed: id, user_id, next_due_date, is_active)

-- debts (auto-indexed: id, user_id, is_active)
-- debt_payments (auto-indexed: id, debt_id, transaction_id)

-- assets (auto-indexed: id, user_id, asset_type, is_active)

-- receipt_ocr (auto-indexed: id, transaction_id)
```

---

## Important Notes

1. **Database:** `finance_db` (bukan `finance`), user `finance_user`, password `finance_pass`
2. **Container:** Docker container `finance_db`, port `5432`
3. **Enum Values:** Selalu UPPERCASE untuk TransactionType (`INCOME`, `EXPENSE`, dll)
4. **Soft Delete:** Selalu set `is_deleted = false` saat INSERT transaksi baru
5. **Time Zone:** `created_at` disimpan dalam UTC. Konversi ke WIB (UTC+7) untuk tampilan
6. **Amount:** Selalu positif, gunakan `NUMERIC(15,2)` untuk presisi keuangan
7. **TransactionType:** Nilai yang valid adalah `INCOME`, `EXPENSE`, `SAVING`, `INVESTMENT`, `DEBT`, dan `TRANSFER`
