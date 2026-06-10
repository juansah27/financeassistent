# 🌌 Hermes Agent SOUL — Database Entry Guide

Panduan operasional untuk pengisian dan pemeliharaan data dalam ekosistem `finance_db`. File ini adalah "Soul" dari agen, memastikan integritas data dan konsistensi pelaporan.

---

## 🛠️ PRINSIP DASAR (Golden Rules)

1.  **TransactionType UPPERCASE**: Selalu gunakan `'INCOME'`, `'EXPENSE'`, `'SAVING'`, `'INVESTMENT'`, `'DEBT'`, atau `'TRANSFER'`.
2.  **Soft Delete**: Jangan pernah gunakan `DELETE`. Selalu gunakan `is_deleted = true`.
3.  **Positive Amounts**: Kolom `amount` selalu positif. Arah aliran dana ditentukan oleh `TransactionType`.
4.  **Audit Trail**: Isi `raw_input` untuk transaksi guna melacak asal-usul data dari user.
5.  **UTF-8 Encoding**: Semua data string harus mendukung karakter khusus (emoticon, dll).
6.  **Akun & Transfer**: Selalu sertakan `account_id` jika diketahui. Untuk `TRANSFER`, wajib menyertakan `account_id` (sumber) dan `destination_account_id` (tujuan).

---

## 👥 USER & FAMILY MANAGEMENT

### 1. `users` & `families`
Digunakan saat inisialisasi user baru atau pembentukan grup keluarga.

```sql
-- Tambah Keluarga Baru
INSERT INTO families (name, join_code) 
VALUES ('Keluarga Juansah', 'HRE-2026');

-- Tambah User Baru
INSERT INTO users (username, pin_hash, family_id) 
VALUES ('Juansah', 'hashed_pin_here', 1);
```

### 2. `family_members`
Penting untuk filter laporan "Siapa yang belanja?".

```sql
INSERT INTO family_members (user_id, name, role, is_active)
VALUES (1, 'Sella', 'Istri', true);
```

---

## 💰 MANAJEMEN REKENING (`accounts`)

Selalu pastikan dari mana uang berasal atau ke mana uang disimpan.

```sql
INSERT INTO accounts (user_id, name, type, balance, is_active)
VALUES 
(1, 'BCA Utama', 'BANK', 15000000.00, true),
(1, 'GoPay', 'EWALLET', 500000.00, true),
(1, 'Dompet Tunai', 'CASH', 200000.00, true);
```

---

## 💸 TRANSAKSI UTAMA (`transactions`)

Tabel paling aktif. Pastikan `is_deleted` selalu `false`. Gunakan `tags` jika ada konteks tambahan.

```sql
INSERT INTO transactions (
    user_id, type, amount, category, 
    description, raw_input, family_member_id, account_id, tags, notes, is_deleted
) VALUES (
    1, 'EXPENSE', 50000.00, 'Makanan', 
    'Beli Nasi Padang', 'nasi padang 50rb pake gopay', 
    2, 2, '#MakanSiang', 'Makan siang bareng', false
);
```

### Transaksi Transfer (Pindah Dana)
Jika pengguna memindahkan uang dari satu rekening ke rekening lain miliknya.

```sql
-- Transfer 1 Juta dari BCA ke GoPay
INSERT INTO transactions (
    user_id, type, amount, category, description,
    account_id, destination_account_id, is_deleted
) VALUES (
    1, 'TRANSFER', 1000000.00, 'Transfer', 'Topup GoPay',
    1, 2, false
);

-- Update saldo akun (Opsional, tergantung logic backend)
UPDATE accounts SET balance = balance - 1000000.00 WHERE id = 1;
UPDATE accounts SET balance = balance + 1000000.00 WHERE id = 2;
```

---

## 📅 BUDGETING (`budgets`)

Target pengeluaran bulanan.

```sql
INSERT INTO budgets (user_id, category, amount, year, month)
VALUES (1, 'Makanan', 2000000.00, 2026, 5);
```

---

## 🔁 RECURRING & INCOME

### 1. `recurring_transactions` (Tagihan Rutin)
```sql
INSERT INTO recurring_transactions (
    user_id, type, amount, category, description, 
    recurrence_type, day_of_month, next_due_date, is_active
) VALUES (
    1, 'EXPENSE', 150000.00, 'Tagihan', 'Netflix HD', 
    'MONTHLY', 15, '2026-05-15 00:00:00+07', true
);
```

### 2. `recurring_income` (Gaji/Passive Income)
```sql
INSERT INTO recurring_income (user_id, name, amount, category, frequency, status)
VALUES (1, 'Gaji Utama', 10000000.00, 'Gaji', 'MONTHLY', 'ACTIVE');
```

---

## 🛡️ DEBT MANAGEMENT (`debts`)

Melacak hutang dan cicilan.

```sql
INSERT INTO debts (
    user_id, type, creditor, name, total_amount, 
    remaining_amount, installment_amount, due_date
) VALUES (
    1, 'BANK', 'BCA', 'KPR Rumah', 500000000.00, 
    450000000.00, 3500000.00, '2026-05-25'
);

-- Record Pembayaran Cicilan
INSERT INTO debt_payments (debt_id, transaction_id, amount, notes)
VALUES (1, 123, 3500000.00, 'Cicilan bulan Mei');
```

---

## 💎 ASSET TRACKING (`assets`)

Memantau kekayaan bersih (Net Worth).

```sql
INSERT INTO assets (user_id, asset_type, name, current_value, quantity, unit)
VALUES (1, 'GOLD', 'Logam Mulia Antam', 12500000.00, 10.0, 'gram');

-- Update History jika nilai berubah
INSERT INTO asset_history (asset_id, old_value, new_value, updated_by_user_id, notes)
VALUES (1, 12000000.00, 12500000.00, 1, 'Kenaikan harga emas global');
```

---

## 🔍 INTELLIGENCE & AUTO-MAPPING

### `transaction_keywords`
Mapping otomatis input user ke kategori yang benar.

```sql
INSERT INTO transaction_keywords (keyword, category)
VALUES ('pertamax', 'Transportasi'), ('gopay', 'Top Up');

### `user_categories`
Kategori kustom untuk user tertentu.

```sql
INSERT INTO user_categories (user_id, name, type, icon, color)
VALUES (1, 'Hobi Game', 'expense', '🎮', '#FF5733');
```

---

## ⚙️ PREFERENCES & SETTINGS

### `user_preferences`
```sql
INSERT INTO user_preferences (user_id, dark_mode, base_currency_code, start_of_month)
VALUES (1, true, 'IDR', 25);
```

---

## 🎯 GOALS & NOTIFICATIONS

### `goals` (Tabungan Impian)
```sql
INSERT INTO goals (user_id, name, target_amount, target_date)
VALUES (1, 'Liburan ke Jepang', 50000000.00, '2027-12-31');
```

### `notifications`
```sql
INSERT INTO notifications (user_id, title, message, notification_type)
VALUES (1, 'Budget Alert!', 'Pengeluaran Makanan sudah 90%', 'budget');
```

---

## 🤖 BOT & WHATSAPP CONFIG

### `whatsapp_report_schedules`
```sql
INSERT INTO whatsapp_report_schedules (user_id, is_enabled, report_time, group_name)
VALUES (1, true, '08:00', 'Keluarga Bahagia');
```

---

> [!IMPORTANT]
> Selalu verifikasi data sebelum eksekusi. Gunakan `SELECT` terlebih dahulu untuk memastikan ID referensi (user_id, debt_id, dll) sudah benar.
