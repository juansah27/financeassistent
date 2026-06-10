# WhatsApp Bot Troubleshooting Guide (Baileys Edition)

## ⚠️ Bot Error / Session Corrupt

Jika bot mengalami error berulang atau tidak bisa terhubung setelah restart app (misal karena mati lampu saat writing session), kemungkinan session data korup.

### Gejala
- Logs menunjukkan error terus menerus saat startup
- `Baileys Client is ready!` tidak pernah muncul
- Error seperti `SyntaxError` di file JSON session

### Cara Memperbaiki (Reset Session)
Karena kita menggunakan `useMultiFileAuthState`, kita bisa reset autentikasi dengan mudah:

1. **Stop container bot:**
   ```bash
   docker-compose stop whatsapp-bot
   ```

2. **Hapus folder auth (Reset QR):**
   ```bash
   # Hapus volume atau folder auth_info secara manual
   # Cara paling aman menggunakan Docker:
   docker-compose down
   docker volume rm financeassistent_whatsapp_auth
   ```
   *Catatan: Ini akan menghapus login session. Anda harus scan QR code lagi.*

3. **Start ulang:**
   ```bash
   docker-compose up -d --build whatsapp-bot
   ```

4. **Scan QR Code:**
   Cek logs untuk QR code baru:
   ```bash
   docker-compose logs -f whatsapp-bot
   ```

## ⚠️ Bot Ready tapi Tidak Menerima Pesan

Jika bot sudah ready (`Baileys Client is ready!`) tapi tidak ada logs ketika mengirim pesan di grup:

### Langkah 1: Pastikan Bot Benar-benar di Grup

1. **Buka grup WhatsApp di smartphone**
2. **Lihat daftar anggota grup** (tap nama grup → lihat anggota)
3. **Pastikan nomor bot ada di daftar**

### Langkah 2: Cek Logs

Setelah restart, bot akan log pesan masuk.

```bash
docker-compose logs -f whatsapp-bot
```

**Harus muncul:**
- `📨 Processing message: "Pesan Anda..."`
- `✅ Webhook success`
- `✅ Reply sent!`

**Jika tidak muncul sama sekali:**
- Bot mungkin diblokir WhatsApp (jarang terjadi di Baileys)
- Cek koneksi internet server

## Masalah: Pesan Tidak Dibalas (Webhook Error)

Jika logs menunjukkan: `❌ Error sending to webhook: ...`

1. **Cek Koneksi ke Backend:**
   Pastikan service `web` berjalan:
   ```bash
   docker-compose ps
   ```

2. **Cek Webhook Secret:**
   Pastikan `WEBHOOK_SECRET` di `.env` sama untuk kedua service.

## FAQ Stabilitas

**Q: Jika Server Mati / Restart, apakah session aman?**
A: **Ya, aman.** Baileys menggunakan login multi-file. Jika server mati mendadak, kemungkinan corrupt sangat kecil karena file session terpecah-pecah. Jika corrupt, biasanya hanya perlu re-scan QR.

**Q: Apakah perlu scan QR setiap restart?**
A: **Tidak.** Session disimpan di volume docker. Selama volume tidak dihapus, bot akan auto-login.

**Q: Berapa lama session bertahan?**
A: WhatsApp biasanya mempertahankan session selama berbulan-bulan aktif. Jika bot mati terlalu lama (misal 2 minggu), mungkin perlu scan ulang.
