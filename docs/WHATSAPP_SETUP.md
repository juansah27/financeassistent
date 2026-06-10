# WhatsApp Bot Setup Guide

Bot WhatsApp untuk membaca transaksi dari grup WhatsApp dan otomatis menambahkannya ke aplikasi.

## Cara Setup

### 1. Update `.env` file

Tambahkan konfigurasi berikut ke file `.env`:

```env
WEBHOOK_SECRET=your-secret-key-here-change-this
ALLOWED_GROUPS=Happy Family 🥰,Finance Group
```

**Penting**: 
- Ganti `your-secret-key-here-change-this` dengan string rahasia yang kuat untuk keamanan webhook.
- `ALLOWED_GROUPS`: Daftar grup yang diizinkan (pisahkan dengan koma). Kosongkan untuk membaca dari semua grup.
  - Contoh: `ALLOWED_GROUPS=Happy Family 🥰,Finance Group`
  - Atau kosongkan: `ALLOWED_GROUPS=` (akan membaca dari semua grup)

### 2. Build dan jalankan aplikasi

```bash
docker-compose up --build
```

### 3. Scan QR Code

Setelah container `whatsapp-bot` berjalan, Anda akan melihat QR code di terminal/logs:

```bash
docker-compose logs whatsapp-bot
```

1. Buka WhatsApp di smartphone Anda
2. Pergi ke **Settings** → **Linked Devices**
3. Pilih **Link a Device**
4. Scan QR code yang muncul di terminal/logs
5. Bot akan terhubung dan siap menerima pesan

### 4. Tambahkan Bot ke Grup WhatsApp

**Langkah-langkah:**

1. **Pastikan bot sudah terhubung:**
   - Bot harus sudah scan QR code dan terhubung
   - Cek logs untuk memastikan: `docker-compose logs whatsapp-bot`
   - Harus ada pesan "WhatsApp Bot is ready!"

2. **Dapatkan nomor bot:**
   - **Cara 1**: Setelah bot terhubung, cek logs bot:
     ```bash
     docker-compose logs whatsapp-bot
     ```
     Akan muncul pesan seperti: `Bot phone number: 6281234567890`
   
   - **Cara 2**: Cek di WhatsApp → Settings → Linked Devices
     - Nomor yang terhubung adalah nomor bot
     - Format: biasanya tanpa tanda + (contoh: 6281234567890)
   
   - **Cara 3**: Setelah scan QR code, nomor bot adalah nomor WhatsApp yang digunakan untuk scan QR code tersebut
   
   **Contoh format nomor bot:**
   - Indonesia: `6281234567890` (tanpa +, tanpa 0 di depan)
   - Format internasional: `+6281234567890` (dengan +)

3. **Tambahkan bot ke grup:**
   - Buka WhatsApp di smartphone
   - Buka grup yang ingin digunakan (atau buat grup baru)
   - Tap menu grup (ikon "i" atau nama grup)
   - Pilih "Add participant" atau "Tambah peserta"
   - Cari nomor bot di kontak WhatsApp Anda
   - Atau ketik nomor bot secara manual (dengan format internasional, contoh: +6281234567890)
   - Tap "Add" atau "Tambah"

4. **Verifikasi bot sudah di grup:**
   - Bot akan muncul sebagai anggota grup
   - Bot akan otomatis membaca pesan transaksi dari grup
   - Bot tidak akan mengirim pesan balik (untuk menghindari spam)

**Catatan Penting:**
- Bot hanya membaca pesan dari **grup WhatsApp**, bukan chat personal
- Bot hanya membaca pesan **baru** setelah bot ditambahkan ke grup
- Bot tidak membaca pesan lama (sebelum bot ditambahkan)

## Cara Menggunakan

### Format Pesan Transaksi

Kirim pesan transaksi di grup WhatsApp dengan format natural language (Bahasa Indonesia):

**Contoh Pemasukan:**
- "Terima gaji 5 juta"
- "Terima bonus 2 juta"
- "Pemasukan 1.5 juta"

**Contoh Pengeluaran:**
- "Beli susu bayi 135 ribu"
- "Bayar listrik 200 ribu"
- "Beli bensin 50 ribu debit"
- "Makan siang 75 ribu"

### Fitur Bot

- ✅ Otomatis membaca pesan dari grup WhatsApp
- ✅ Menggunakan AI untuk parse transaksi (sama seperti di web app)
- ✅ Mendeteksi pemasukan/pengeluaran
- ✅ Extract jumlah (ribu, rb, juta, jt)
- ✅ Assign kategori otomatis
- ✅ Menambahkan transaksi ke database

### Keamanan

- Bot hanya membaca pesan dari **grup WhatsApp** (bukan chat personal)
- Webhook menggunakan secret key untuk autentikasi
- Bot tidak mengirim pesan balik ke grup (untuk menghindari spam)

## Troubleshooting

### Bot tidak terhubung

1. Pastikan container `whatsapp-bot` berjalan:
   ```bash
   docker-compose ps
   ```

2. Cek logs untuk QR code:
   ```bash
   docker-compose logs -f whatsapp-bot
   ```

3. Jika QR code expired, restart container:
   ```bash
   docker-compose restart whatsapp-bot
   ```

### Bot tidak membaca pesan

1. **Cek bot sudah terhubung:**
   ```bash
   docker-compose logs whatsapp-bot | grep "ready"
   ```
   Harus muncul: `WhatsApp Bot is ready!`

2. **Cek bot menerima pesan:**
   - Kirim pesan di grup
   - Cek logs: `docker-compose logs -f whatsapp-bot`
   - Harus muncul: `📨 Message received` atau `📝 [Nama Grup]`

3. **Jika tidak muncul pesan di logs:**
   - Bot belum ditambahkan ke grup WhatsApp
   - Bot tidak terhubung dengan benar
   - Restart bot: `docker-compose restart whatsapp-bot`

4. **Jika muncul tapi tidak diproses:**
   - Pastikan pesan mengandung kata kunci transaksi atau angka
   - Kata kunci: beli, bayar, terima, gaji, ribu, juta, rb, jt
   - Pesan harus >= 5 karakter
   - Cek logs untuk alasan di-skip

5. **Lihat troubleshooting lengkap:**
   Lihat file `WHATSAPP_TROUBLESHOOTING.md` untuk panduan debugging lengkap

### Transaksi tidak dibuat

1. Cek webhook endpoint berfungsi:
   ```bash
   curl http://localhost:8000/api/whatsapp/status
   ```

2. Cek logs web untuk error:
   ```bash
   docker-compose logs web
   ```

### QR Code tidak muncul

1. Hapus folder `auth` dan restart:
   ```bash
   docker-compose down
   docker volume rm financeassistent_whatsapp_auth
   docker-compose up --build
   ```

### Reset Bot untuk Mengganti Nomor WhatsApp

Jika ingin menggunakan nomor WhatsApp lain:

1. **Stop bot:**
   ```bash
   docker-compose stop whatsapp-bot
   ```

2. **Hapus auth data:**
   ```bash
   docker-compose down
   docker volume rm financeassistent_whatsapp_auth
   ```

3. **Start bot lagi:**
   ```bash
   docker-compose up --build
   ```

4. **Scan QR code dengan nomor baru:**
   - Buka WhatsApp di smartphone dengan nomor yang ingin digunakan
   - Settings → Linked Devices → Link a Device
   - Scan QR code yang muncul di logs

**Catatan:** Bot menggunakan nomor WhatsApp yang digunakan untuk scan QR code. Tidak ada "nomor bot khusus" - bot menggunakan WhatsApp Web dari nomor yang digunakan untuk scan.

Lihat `WHATSAPP_RESET.md` untuk panduan lengkap reset bot.

## Catatan Penting

- Bot menggunakan **whatsapp-web.js** yang terhubung ke WhatsApp Web
- Bot perlu tetap terhubung (container harus running)
- Jika WhatsApp Web logout, bot perlu scan QR code lagi
- Bot hanya membaca pesan baru setelah bot ditambahkan ke grup
- Bot tidak membaca pesan lama (sebelum bot ditambahkan)

## Advanced Configuration

### Mengubah User Default

Default bot akan menambahkan transaksi ke user pertama di database. Untuk mengubah ini, edit `app/routes/whatsapp.py` dan tambahkan mapping `sender_number` ke `user_id`.

### Mengaktifkan Reply ke Grup

Uncomment bagian reply di `whatsapp-bot/bot.js` jika ingin bot mengirim konfirmasi kembali ke grup:

```javascript
// Uncomment untuk mengirim konfirmasi
await message.reply(replyMessage);
```

**Peringatan**: Ini bisa menyebabkan spam jika banyak transaksi.

## Support

Jika ada masalah, cek:
1. Logs container: `docker-compose logs whatsapp-bot`
2. Logs web: `docker-compose logs web`
3. Status endpoint: `http://localhost:8000/api/whatsapp/status`

