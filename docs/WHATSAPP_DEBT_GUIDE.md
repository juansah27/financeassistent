# 💬 Panduan Penggunaan WhatsApp Bot untuk Debt Management

## 📱 Fitur WhatsApp Bot yang Sudah Ada

### 1. **Notifikasi Otomatis Reminder** ✅
WhatsApp bot akan **otomatis mengirim reminder** setiap hari jam **07:00 pagi** untuk:

- **Hutang jatuh tempo HARI INI** (🔴)
- **Hutang jatuh tempo BESOK** (🔴)
- **Hutang jatuh tempo 3 hari lagi** (🔴)
- **Hutang jatuh tempo 7 hari lagi** (⚠️)
- **Hutang yang TELAT bayar** (❌)

**Contoh Pesan:**
```
📅 REMINDER PEMBAYARAN HUTANG
━━━━━━━━━━━━━━━━━━━━━━━

🔴 Shopee PayLater
   Jatuh tempo: 12 Jan (3 hari lagi)
   Jumlah: Rp 400.000
   Cicilan: 4/12

⚠️ BCA Credit Card
   Jatuh tempo: 15 Jan (6 hari lagi)
   Jumlah: Rp 2.000.000

━━━━━━━━━━━━━━━━━━━━━━━
💡 Jangan lupa bayar tepat waktu!
```

### 2. **Laporan Harian Otomatis** ✅
Debt section otomatis muncul dalam **laporan keuangan harian** yang dikirim sesuai jadwal user:

**Contoh:**
```
📊 Laporan Keuangan Harian
📅 Kamis, 09 Januari 2026

💸 Pengeluaran: Rp 125.000
💰 Total Saldo: +Rp 2.500.000
📝 Total Transaksi: 8

💳 HUTANG & TAGIHAN MENDEKATI
━━━━━━━━━━━━━━━━━━━
• Shopee PayLater - 🔴 BESOK
  Rp 400.000
• Motor - ⚠️ 5 hari
  Rp 1.200.000

💡 Insight: Pengeluaran hari ini...
```

---

## 🚫 Fitur yang Belum Ada (Future)

### Interactive Commands (Belum Implemented)
Saat ini user **TIDAK BISA** kirim command ke WhatsApp bot untuk query hutang. Fitur ini bisa ditambahkan nanti:

**Contoh command yang bisa ditambahkan:**
```
User: "hutang"
Bot: Menampilkan daftar semua hutang aktif

User: "hutang minggu ini"  
Bot: Hutang yang jatuh tempo minggu ini

User: "hutang telat"
Bot: Daftar hutang yang telat bayar
```

---

## 💡 Cara Kerja Saat Ini

### Flow Otomatis:
1. **User menambah hutang** via Web UI (http://localhost:8000/debts)
   - Isi: Kreditor, Total, Cicilan, Tenor, **Tanggal Mulai**, Due Date
   - Klik "Simpan Hutang"
   
2. **Backend auto-calculate**:
   - Next payment date = Tanggal Mulai + (Paid Count + 1) bulan
   - Days until due = Next Payment - Today
   
3. **Scheduler job (7 AM)** cek semua user:
   - Query debts due in 0, 1, 3, 7 days
   - Query overdue debts
   - Format WhatsApp message
   
4. **WhatsApp bot kirim** ke group yang terdaftar
   - User dapat notifikasi otomatis
   - No action needed dari user

---

## 🎯 Cara User Menggunakan

### Alur Lengkap:

**Step 1: Setup WhatsApp Report Schedule**
- Buka Settings → WhatsApp Reports
- Enable schedule
- Set group name & ID
- Set report time (e.g., 08:00)

**Step 2: Tambah Hutang via Web**
- Login ke http://localhost:8000/debts
- Klik "Tambah Hutang"
- Isi form:
  ```
  Kreditor: Shopee PayLater
  Total: 1.200.000
  Cicilan: 100.000
  Tenor: 12
  Tanggal Mulai: 2026-01-01
  Due Date: 2026-12-01
  ```
- Klik "Simpan"

**Step 3: Catat Pembayaran**
- Setelah bayar, klik "Bayar" di list
- Isi jumlah pembayaran
- System auto-update: paid_count++, remaining_amount--

**Step 4: Terima WhatsApp Reminder**
- Setiap pagi jam 7, dapat reminder otomatis
- Setiap laporan harian, lihat debt section

---

## ⚙️ Konfigurasi yang Diperlukan

Agar WhatsApp reminder berfungsi, pastikan:

1. ✅ **WhatsApp Bot Running**
   - Service whatsapp-bot up
   - API endpoint: http://whatsapp-bot:3000

2. ✅ **Environment Variables**
   ```bash
   WHATSAPP_BOT_API_URL=http://whatsapp-bot:3000
   WEBHOOK_SECRET=your-secret-key
   ```

3. ✅ **User punya WhatsApp Schedule**
   - Minimal 1 active schedule
   - Group name & ID configured

4. ✅ **Scheduler Running**
   - check_debt_reminders_job registered
   - Runs daily at 07:00 AM

---

## 📝 Summary

| Fitur | Status | Cara Pakai |
|-------|--------|------------|
| **Web UI Input** | ✅ Ready | Via /debts page |
| **Auto Reminders** | ✅ Ready | Otomatis jam 7 pagi |
| **Daily Report Section** | ✅ Ready | Auto-include di laporan |
| **Payment Tracking** | ✅ Ready | Via "Bayar" button |
| **Countdown Badge** | ✅ Ready | Auto-calculate |
| **Interactive Commands** | ❌ Future | Perlu webhook handler |
| **Manual WhatsApp Input** | ❌ Future | Perlu natural language parser |

---

## 🚀 Next Steps (Opsional)

Jika mau tambah interactive commands:

1. Buat webhook handler di whatsapp-bot service
2. Parse incoming messages
3. Detect "hutang" commands
4. Call API `/api/debt`
5. Format response dengan `debt_whatsapp.format_debt_list_response()`
6. Send back to WhatsApp

Tapi untuk sekarang, **reminder otomatis sudah fully functional** dan user cukup manage via web UI! 🎉
