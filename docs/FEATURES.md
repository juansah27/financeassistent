# Fitur-Fitur Baru

## ✅ Fitur yang Sudah Ditambahkan

### 1. Edit & Hapus Transaksi
- **Route**: `/transaction/{id}`, `/transaction/{id}/edit`
- **Fitur**:
  - View detail transaksi
  - Edit amount, category, description, notes
  - Soft delete (bisa di-restore)
  - Edit history tracking
  - Upload & view photos

### 2. Recurring Income (Pemasukan Otomatis)
- **Route**: `/recurring`
- **Fitur**:
  - Support untuk pemasukan berulang (gaji bulanan, dll)
  - Auto-create transaksi saat jatuh tempo
  - Toggle aktif/nonaktif

### 3. Receipt OCR
- **Service**: `app/services/ocr.py`
- **Fitur**:
  - Auto-extract data dari foto struk menggunakan OpenAI Vision
  - Extract: merchant name, total amount, date, items
  - Auto-update transaction dari OCR result

### 4. Multi-Currency Support
- **Models**: `Currency`, `UserPreference`
- **Fitur**:
  - Support multiple currencies
  - Auto-convert ke base currency
  - Set base currency per user
  - Default: IDR, USD

### 5. Family Member Tagging
- **Models**: `FamilyMember`
- **Fitur**:
  - Tambah anggota keluarga
  - Tag transaksi dengan anggota keluarga
  - Spending breakdown per anggota
  - Settings: `/settings`

### 6. Advanced Reports
- **Route**: `/reports/advanced`, `/reports/pdf`
- **Fitur**:
  - Yearly summary
  - PDF export dengan ReportLab
  - Multi-month comparison
  - Category trends

### 7. Dark Mode
- **Implementation**: CSS classes + localStorage
- **Fitur**:
  - Toggle dark/light theme
  - Persist preference
  - Settings: `/settings`

### 8. Data Analytics Dashboard
- **Route**: `/analytics`
- **Fitur**:
  - Spending patterns (12 months)
  - Category trends
  - Family member spending breakdown
  - Average vs current month comparison
  - Charts dengan Chart.js

### 9. Backup & Restore
- **Route**: `/backup`
- **Fitur**:
  - Export to CSV
  - Export full backup (JSON)
  - Import backup
  - Auto-backup functionality

## 📁 File Struktur Baru

```
app/
├── db/
│   ├── models.py (updated)
│   ├── crud_extended.py
│   ├── crud_new_features.py (NEW)
│   └── migrate.py (updated)
├── routes/
│   ├── transactions.py (NEW)
│   ├── analytics.py (NEW)
│   ├── backup_restore.py (NEW)
│   ├── settings.py (NEW)
│   └── reports_advanced.py (NEW)
├── services/
│   ├── ocr.py (NEW)
│   └── backup.py (NEW)
└── templates/
    ├── transaction_detail.html (NEW)
    ├── transaction_edit.html (NEW)
    ├── settings.html (NEW)
    ├── analytics.html (NEW)
    ├── backup.html (NEW)
    └── base.html (NEW)
```

## 🗄️ Database Schema Baru

### New Tables:
- `currencies` - Mata uang
- `family_members` - Anggota keluarga
- `transaction_edits` - Riwayat edit transaksi
- `receipt_ocr` - Data OCR dari foto
- `user_preferences` - Preferensi user (dark mode, currency, dll)

### Updated Tables:
- `transactions` - Added: `family_member_id`, `currency_code`, `amount_in_base_currency`, `notes`, `is_deleted`, `deleted_at`

## 🚀 Cara Menggunakan

### 1. Run Migration
```bash
docker-compose exec web python -m app.db.migrate
```

### 2. Access New Features
- **Edit Transaction**: Klik transaksi → Edit
- **Analytics**: `/analytics`
- **Settings**: `/settings`
- **Backup**: `/backup`
- **Advanced Reports**: `/reports/advanced`

### 3. Dark Mode
- Settings → Toggle Dark Mode
- Preference tersimpan di localStorage

### 4. OCR Receipt
- Upload foto di detail transaksi
- OCR akan otomatis extract data
- Transaction akan auto-update jika OCR berhasil

## 📝 Notes

- **OCR**: Membutuhkan OpenAI API key dengan akses ke GPT-4 Vision
- **PDF Export**: Menggunakan ReportLab library
- **Dark Mode**: Menggunakan Tailwind CSS dark mode classes
- **Backup**: File disimpan di `app/static/backups/`

