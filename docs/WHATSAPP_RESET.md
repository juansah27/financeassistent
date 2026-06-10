# Cara Reset WhatsApp Bot

## Reset Bot untuk Mengganti Nomor WhatsApp

Bot WhatsApp menggunakan WhatsApp Web, jadi bot akan menggunakan nomor WhatsApp yang digunakan untuk scan QR code. Jika ingin menggunakan nomor lain, ikuti langkah berikut:

### 1. Stop Bot

```bash
docker-compose stop whatsapp-bot
```

### 2. Hapus Auth Data (Reset)

```bash
docker-compose down
docker volume rm financeassistent_whatsapp_auth
```

Atau jika ingin menghapus semua data:
```bash
docker-compose down -v
```

### 3. Start Bot Lagi

```bash
docker-compose up --build
```

### 4. Scan QR Code dengan Nomor Baru

1. Buka WhatsApp di smartphone dengan nomor yang ingin digunakan
2. Pergi ke **Settings** → **Linked Devices** → **Link a Device**
3. Scan QR code yang muncul di logs: `docker-compose logs whatsapp-bot`
4. Bot akan terhubung dengan nomor baru

## Catatan Penting

### Bot Menggunakan Nomor WhatsApp yang Digunakan untuk Scan QR Code

- Bot **TIDAK** memiliki nomor sendiri
- Bot menggunakan WhatsApp Web dari nomor yang digunakan untuk scan QR code
- Jika scan dengan nomor A, bot akan menggunakan nomor A
- Jika scan dengan nomor B, bot akan menggunakan nomor B

### Opsi untuk Menggunakan Nomor Terpisah

**Opsi 1: Buat Nomor WhatsApp Baru**
- Daftar nomor WhatsApp baru (bisa pakai nomor kedua atau nomor khusus)
- Scan QR code dengan nomor baru tersebut
- Bot akan menggunakan nomor baru

**Opsi 2: Gunakan WhatsApp Business**
- Buat akun WhatsApp Business (gratis)
- Scan QR code dengan WhatsApp Business
- Bot akan menggunakan nomor WhatsApp Business

**Opsi 3: Gunakan Nomor Pribadi (Saat Ini)**
- Tetap menggunakan nomor pribadi Anda
- Bot akan membaca pesan dari grup yang nomor Anda ikuti
- Tidak masalah menggunakan nomor pribadi untuk bot

### Keamanan

- Bot hanya membaca pesan dari **grup WhatsApp**
- Bot tidak membaca chat personal
- Bot tidak mengirim pesan balik (default)
- Data auth tersimpan di Docker volume (aman)

## Troubleshooting

### QR Code Tidak Muncul Setelah Reset

```bash
# Pastikan volume sudah dihapus
docker volume ls | grep whatsapp_auth

# Jika masih ada, hapus manual
docker volume rm financeassistent_whatsapp_auth

# Restart
docker-compose up --build
```

### Bot Masih Menggunakan Nomor Lama

Pastikan:
1. Volume `whatsapp_auth` sudah dihapus
2. Container sudah di-rebuild
3. Scan QR code dengan nomor baru (bukan nomor lama)

### Ingin Menggunakan Nomor yang Sama

Jika ingin tetap menggunakan nomor yang sama, cukup scan QR code lagi dengan nomor yang sama setelah reset.

