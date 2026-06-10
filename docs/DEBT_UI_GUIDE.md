# 🎨 Cara Melihat & Menggunakan UI Hutang & Kredit

## ✅ Akses Halaman Hutang

### 1. **Buka Browser**
```
http://localhost:8000/debts
```

### 2. **Via Navigation Sidebar**
Klik menu **"Hutang & Kredit"** di sidebar kiri

---

## 🎯 Fitur-Fitur UI

### 1. **Quick Input dengan AI** 🤖

**Cara pakai:**
1. Ketik langsung di kolom "Input Cepat"
2. Contoh input:
   - `Hutang ke Andi 3 juta`
   - `Shopee PayLater 500 ribu`
   - `Kredit motor 15jt 12 bulan`
   - `Kartu kredit BCA 2 juta`
3. Klik tombol **"Proses"**
4. AI akan otomatis parse dan form akan terisi!
5. Klik **"Simpan Hutang"**

**Keuntungan:**
✨ AI otomatis detect:
- Jenis hutang (personal, paylater, bank, dll)
- Nominal
- Kreditor/platform
- Tenor dan cicilan (jika ada)

---

### 2. **Summary Cards** 📊

Di bagian atas ada 4 kartu:
- **Total Hutang**: Total semua hutang
- **Sisa Belum Dibayar**: Berapa yang masih harus dibayar
- **PayLater**: Total dari Kredivo, Shopee, dll
- **Kartu Kredit**: Total dari BCA, Mandiri, dll

**Update otomatis** setiap kali ada perubahan!

---

### 3. **Daftar Hutang** 📋

**Fitur:**
- Filter berdasarkan tipe (Personal, Bank, PayLater, dll)
- Lihat detail setiap hutang
- Button "Bayar" untuk catat pembayaran

**Kolom yang ditampilkan:**
- Kreditor (nama pemberi hutang)
- Tipe (badge warna-warni)
- Total hutang
- Sisa yang harus dibayar
- Progress cicilan (e.g., "3/12")

---

### 4. **Catat Pembayaran** 💰

**Cara pakai:**
1. Klik button **"Bayar"** di daftar hutang
2. Modal akan muncul
3. Isi:
   - Jumlah pembayaran
   - Sumber dana (optional)
   - Catatan (optional)
4. Klik **"Catat Pembayaran"**

**Otomatis:**
- Mengurangi sisa hutang
- Update progress cicilan
- Jika lunas, status berubah jadi "Paid Off"

---

## 🎨 Preview UI

### Screenshot Simulasi:

```
┌─────────────────────────────────────────────┐
│  Hutang & Kredit              [+ Tambah]    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐│
│  │ 15jt  │  │ 10jt  │  │ 2jt   │  │ 3jt   ││
│  │ Total │  │ Sisa  │  │PayLtr │  │CC     ││
│  └───────┘  └───────┘  └───────┘  └───────┘│
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │ 💬 Input Cepat: "Shopee PayLater 500rb"││
│  │                             [Proses]    ││
│  └─────────────────────────────────────────┘│
│                                             │
│  Daftar Hutang           [Filter: Semua v] │
│  ┌─────────────────────────────────────────┐│
│  │ Shopee PayLater    PayLater  500,000   ││
│  │ Sisa: 300,000      2/3       [Bayar]   ││
│  ├─────────────────────────────────────────┤│
│  │ BCA Credit Card    CC        2,000,000 ││
│  │ Sisa: 2,000,000    -         [Bayar]   ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Scenario 1: Tambah Hutang Manual
```
1. Klik [+ Tambah Hutang]
2. Isi form:
   - Kreditor: "Andi"
   - Tipe: "Personal"
   - Total: 3000000
3. Klik "Simpan"
```

### Scenario 2: Tambah Hutang dengan AI
```
1. Ketik: "Hutang ke Andi 3 juta"
2. Klik "Proses"
3. Form otomatis terisi!
4. Klik "Simpan"
```

### Scenario 3: Bayar Cicilan
```
1. Cari hutang di daftar
2. Klik "Bayar"
3. Isi jumlah: 1000000
4. Klik "Catat Pembayaran"
```

---

## 🎯 Contoh Real-World Usage

### Skenario Lengkap:

**Hari 1: Pinjam Uang**
```
Input: "Shopee PayLater 1,2 juta cicilan 3 bulan"
AI Parse:
- Type: paylater
- Creditor: Shopee PayLater
- Amount: 1,200,000
- Tenor: 3
- Installment: 400,000
```

**Hari 30: Bayar Cicilan Pertama**
```
Klik "Bayar" → Isi 400,000 → Submit
Status sekarang: 
- Sisa: 800,000
- Progress: 1/3
```

**Hari 60: Bayar Cicilan Kedua**
```
Klik "Bayar" → Isi 400,000 → Submit
Status sekarang:
- Sisa: 400,000
- Progress: 2/3
```

**Hari 90: Lunas!**
```
Klik "Bayar" → Isi 400,000 → Submit
Status: ✅ PAID OFF
Sisa: 0
```

---

## 💡 Tips & Tricks

### Tip 1: Multi-Platform PayLater
```
✅ Shopee PayLater 500 ribu
✅ Kredivo 1 juta
✅ Akulaku 750 ribu
```
Semua terdeteksi otomatis sebagai "paylater"!

### Tip 2: Kartu Kredit Multiple
```
✅ Kartu kredit BCA 2 juta
✅ CC Mandiri 1,5 juta
```
Auto-detect bank dari nama!

### Tip 3: Filter Cepat
Gunakan dropdown filter untuk:
- Lihat hanya PayLater
- Lihat hanya Credit Card
- Lihat hanya Personal loans

---

## 🐛 Troubleshooting

### Problem: UI tidak muncul?
**Solution:**
```bash
# Restart container
docker-compose restart web

# Cek logs
docker-compose logs web
```

### Problem: AI tidak detect?
**Solution:**
- Pastikan format jelas: "[kreditor] [jumlah]"
- Contoh yang benar: "Hutang ke Andi 3 juta"
- Bad: "3 juta andi" ← terlalu ambigu

### Problem: Data tidak muncul?
**Solution:**
```bash
# Cek API
curl http://localhost:8000/api/debt

# Should return JSON with debts list
```

---

## 📸 Screenshots (Simulasi)

### 1. Dashboard Summary
- **Total Hutang**: Rp 15.000.000
- **Sisa**: Rp 10.000.000
- **PayLater**: Rp 2.000.000 (3 platform)
- **Credit Card**: Rp 3.000.000 (2 kartu)

### 2. Quick AI Input
```
Input: "Shopee PayLater 500 ribu"
Result: ✨ Terdeteksi AI (Confidence: 90%)
- Kreditor: Shopee PayLater
- Tipe: paylater
- Jumlah: Rp 500.000
```

### 3. Payment Modal
```
┌──────────────────────────┐
│ Catat Pembayaran         │
├──────────────────────────┤
│ Jumlah: [1,000,000]      │
│ Sumber: [Rekening BCA]   │
│ Notes: [Cicilan bulan 1] │
│                          │
│   [Batal]  [Catat ✓]   │
└──────────────────────────┘
```

---

## 🎊 Ready to Use!

UI sudah **LIVE** di:
```
http://localhost:8000/debts
```

Langsung bisa dipake sekarang! 🚀

### Navigation:
Dashboard → Sidebar → **"Hutang & Kredit"** → Enjoy! ✨
