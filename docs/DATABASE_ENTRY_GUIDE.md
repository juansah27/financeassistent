# 🗄️ Panduan Lengkap Pengisian Database (`finance_db`)

Dokumentasi ini berisi panduan komprehensif tentang cara melakukan pengisian (INSERT) dan pembaruan data yang benar di dalam database PostgreSQL `finance_db`. Panduan ini dirancang untuk memastikan integritas data dan memandu pengelolaan basis data agar sejalan dengan kebutuhan fungsional aplikasi Finance Assistant.

---

## 🛠️ 1. Koneksi & Akses Database

### Kredensial Database
- **Container:** `finance_db` (PostgreSQL 15)
- **User:** `finance_user`
- **Password:** `finance_pass`
- **Database:** `finance_db`

### Cara Eksekusi Query via Docker
Anda dapat mengeksekusi perintah SQL langsung ke dalam container tanpa harus masuk ke shell container terlebih dahulu, dengan menggunakan perintah berikut:

```bash
docker exec finance_db psql -U finance_user -d finance_db -c "QUERY_SQL_DISINI"
```

---

## ⚖️ 2. Aturan Emas (Golden Rules)

Sebelum melakukan `INSERT` atau `UPDATE`, pastikan Anda mematuhi aturan baku berikut:

1. **Gunakan UPPERCASE untuk ENUM**: Nilai enumerasi seperti tipe transaksi (`INCOME`, `EXPENSE`, `TRANSFER`, dll.), tipe akun (`BANK`, `EWALLET`, dll.), dan tipe aset **wajib** ditulis dengan huruf kapital.
2. **Penerapan Soft Delete**: Tabel utama seperti `transactions` menggunakan sistem "soft delete". Saat menginput transaksi baru, selalu set parameter `is_deleted = false`. Jangan menggunakan perintah `DELETE`.
3. **Nilai Nominal Positif**: Nilai pada kolom `amount` harus selalu positif (`> 0`). Status aliran kas (uang keluar/masuk) ditentukan eksklusif dari kolom `type` (`EXPENSE`, `INCOME`, `SAVING`, dll.).
4. **Relasi Transfer**: Khusus untuk tipe `TRANSFER`, kolom `account_id` wajib diisi sebagai **sumber dana**, dan `destination_account_id` sebagai **tujuan dana**.

---

## 👥 3. Inisialisasi: Keluarga, User, dan Anggota

Struktur utama untuk menentukan kepemilikan dan hak akses entitas.

### Menambahkan Entitas Keluarga Baru
```sql
INSERT INTO families (name, join_code) 
VALUES ('Keluarga Juansah', 'HRE-2026');
```

### Menambahkan Pengguna (User) Baru
```sql
-- Pastikan family_id sesuai dengan id keluarga yang telah dibuat
INSERT INTO users (username, pin_hash, family_id) 
VALUES ('Juansah', 'hashed_pin_here', 1);
```

### Menambahkan Anggota Keluarga (Untuk Tagging Pelaku Transaksi)
Data ini digunakan sebagai penanda siapakah anggota keluarga (istri, anak, suami) yang melakukan pembelanjaan/pemasukan.
```sql
INSERT INTO family_members (user_id, name, role, is_active)
VALUES 
(1, 'Sella', 'Istri', true), 
(1, 'Gavin', 'Anak', true);
```

---

## 💳 4. Manajemen Akun (Dompet & Rekening)

Semua transaksi finansial harus terhubung dengan sebuah dompet kas atau rekening akun bank.

```sql
INSERT INTO accounts (user_id, name, type, balance, is_active)
VALUES 
(1, 'BCA Utama', 'BANK', 15000000.00, true),
(1, 'GoPay', 'EWALLET', 500000.00, true),
(1, 'Dompet Tunai', 'CASH', 200000.00, true);
```
> **Catatan:** ENUM Tipe akun yang didukung adalah: `BANK`, `EWALLET`, `CASH`, dan `INVESTMENT`.

---

## 💸 5. Pencatatan Transaksi (`transactions`)

Ini merupakan tabel paling aktif dimana seluruh aliran dana masuk/keluar dicatat.

### Transaksi Pemasukan / Pengeluaran Standar
```sql
INSERT INTO transactions (
    user_id, type, amount, category, 
    description, raw_input, family_member_id, account_id, tags, is_deleted
) VALUES (
    1, 'EXPENSE', 50000.00, 'Makanan', 
    'Beli Nasi Padang', 'nasi padang 50rb pake gopay', 
    2, 2, '#MakanSiang', false
);
```

### Transaksi Transfer Antar Rekening
Jika uang berpindah dari dompet/rekening A (`account_id`) ke rekening B (`destination_account_id`).
```sql
INSERT INTO transactions (
    user_id, type, amount, category, description,
    account_id, destination_account_id, is_deleted
) VALUES (
    1, 'TRANSFER', 1000000.00, 'Transfer', 'Topup GoPay dari BCA',
    1, 2, false
);
```
> **Penting:** Di dalam sistem produksi, ketika input transaksi transfer dilakukan, saldo (`balance`) pada tabel `accounts` biasanya akan diperbarui secara terpisah di logic backend.

---

## 🛡️ 6. Manajemen Hutang & Cicilan (`debts`)

Sistem melacak keseluruhan detail hutang dan cicilan yang sedang aktif.

### Mencatat Data Pinjaman/Hutang Baru
```sql
INSERT INTO debts (
    user_id, type, creditor, name, total_amount, 
    remaining_amount, installment_amount, due_date, start_date
) VALUES (
    1, 'BANK', 'BCA', 'KPR Rumah', 500000000.00, 
    450000000.00, 3500000.00, '2026-05-25', NOW()
);
```
> **ENUM Tipe Hutang:** `PERSONAL`, `BANK`, `LEASING`, `CREDIT_CARD`, `PAYLATER`, `BILL`.

### Mencatat Pembayaran Cicilan
Ketika ada pembayaran atas cicilan hutang yang aktif.
```sql
INSERT INTO debt_payments (debt_id, transaction_id, amount, payment_date, notes)
VALUES (1, 154, 3500000.00, NOW(), 'Pembayaran KPR Bulan Mei');
```

---

## 💎 7. Pelacakan Kekayaan & Aset (`assets`)

Sistem ini mendukung pencatatan perubahan nilai investasi dan aset (Net Worth).

### Menginput Aset Baru (Pembelian Aset)
```sql
INSERT INTO assets (user_id, asset_type, name, current_value, quantity, unit)
VALUES (1, 'GOLD', 'Logam Mulia Antam', 12500000.00, 10.0, 'gram');
```
> **ENUM Tipe Aset:** `BPJS`, `GOLD`, `PROPERTY`, `VEHICLE`, `DEPOSIT`, `STOCK`, `CRYPTO`.

### Memperbarui Nilai Aset (Histori Fluktuasi)
Saat nilai market sebuah aset berubah (misal: harga emas naik/turun), rekam histori perubahan nilainya, kemudian perbarui `current_value` asetnya:
```sql
-- 1. Rekam jejak perubahan harga
INSERT INTO asset_history (asset_id, old_value, new_value, updated_by_user_id, notes)
VALUES (1, 12000000.00, 12500000.00, 1, 'Update harga referensi emas dunia hari ini');

-- 2. Update harga real pada tabel aset utama
UPDATE assets SET current_value = 12500000.00 WHERE id = 1;
```

---

## 📅 8. Budgeting Bulanan (`budgets`)

Alokasi target anggaran pengeluaran untuk setiap kategori yang berlaku spesifik dalam rentang satu bulan.

```sql
INSERT INTO budgets (user_id, category, amount, year, month)
VALUES 
(1, 'Makanan', 3000000.00, 2026, 5),
(1, 'Transportasi', 1000000.00, 2026, 5);
```

---

## 🔁 9. Transaksi Berulang & Pendapatan Konstan

Data ini digunakan oleh sistem _Cron/Scheduler_ untuk mengeksekusi tagihan atau pemasukan secara otomatis.

### Menambah Tagihan Transaksi Berulang (Contoh: Langganan Bulanan)
```sql
INSERT INTO recurring_transactions (
    user_id, type, amount, category, description, 
    recurrence_type, day_of_month, next_due_date, is_active
) VALUES (
    1, 'EXPENSE', 153000.00, 'Hiburan', 'Netflix Premium', 
    'MONTHLY', 15, '2026-05-15 00:00:00+07', true
);
```

### Menambah Sumber Pendapatan Rutin Berulang (Contoh: Gaji Bulanan)
```sql
INSERT INTO recurring_income (user_id, name, amount, category, frequency, status)
VALUES (1, 'Gaji Utama', 10000000.00, 'Gaji', 'MONTHLY', 'ACTIVE');
```

---

## 🤖 10. Kecerdasan Agen Bot & Pemetaan Cerdas

Fitur pemetaan agar WhatsApp AI Agent dan backend dapat dengan instan mengenali intent.

### Pemetaan Kata Kunci (`transaction_keywords`)
Digunakan oleh bot untuk menerjemahkan ucapan alami pengguna menjadi "kategori baku".
```sql
INSERT INTO transaction_keywords (keyword, category)
VALUES 
('pertamax', 'Transportasi'), 
('pln', 'Tagihan'), 
('indomaret', 'Belanja Harian'),
('makan', 'Makanan');
```

### Konfigurasi Preferensi Pengguna & Laporan Auto-WhatsApp
Mengelola bagaimana AI Agent menampilkan laporan dan berinteraksi.
```sql
-- Pengaturan preferensi personal pengguna
INSERT INTO user_preferences (user_id, dark_mode, base_currency_code, start_of_month)
VALUES (1, false, 'IDR', 1);

-- Pengaturan waktu tembak notifikasi whatsapp terjadwal
INSERT INTO whatsapp_report_schedules (user_id, is_enabled, report_time, group_name)
VALUES (1, true, '07:00', 'Grup Keuangan Keluarga');
```
