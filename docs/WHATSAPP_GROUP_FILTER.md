# Filter Grup WhatsApp Bot

Bot dapat dikonfigurasi untuk hanya membaca pesan dari grup tertentu yang ditentukan.

## Konfigurasi

### 1. Edit File `.env`

Tambahkan `ALLOWED_GROUPS` ke file `.env`:

```env
ALLOWED_GROUPS=Happy Family 🥰,Finance Group,Group Lainnya
```

**Format:**
- Pisahkan nama grup dengan koma (`,`)
- Nama grup tidak case-sensitive (Happy Family = happy family)
- Bisa menggunakan nama grup atau group ID

**Contoh:**
```env
# Hanya membaca dari 2 grup
ALLOWED_GROUPS=Happy Family 🥰,Finance Group

# Membaca dari semua grup (kosongkan)
ALLOWED_GROUPS=

# Atau hapus baris ini untuk membaca dari semua grup
```

### 2. Restart Bot

Setelah mengubah `.env`, restart bot:

```bash
docker-compose restart whatsapp-bot
```

Atau rebuild jika perlu:

```bash
docker-compose down
docker-compose up --build
```

## Cara Mengetahui Nama Grup

Setelah bot ready, cek logs untuk melihat daftar grup:

```bash
docker-compose logs whatsapp-bot | grep "Groups bot is in"
```

Akan muncul:
```
Groups bot is in:
  - Happy Family 🥰 (120363398239342501@g.us) ✅ ALLOWED
  - SI UT JAKARTA (120363258329526364@g.us) ❌ NOT ALLOWED
  - Finance Group (120363207125150660@g.us) ✅ ALLOWED
```

## Menggunakan Group ID

Selain nama grup, bisa juga menggunakan Group ID:

```env
ALLOWED_GROUPS=120363398239342501@g.us,120363207125150660@g.us
```

Group ID bisa dilihat di logs setelah bot ready.

## Contoh Konfigurasi

### Contoh 1: Hanya Satu Grup
```env
ALLOWED_GROUPS=Happy Family 🥰
```

### Contoh 2: Beberapa Grup
```env
ALLOWED_GROUPS=Happy Family 🥰,Finance Group,Family Budget
```

### Contoh 3: Semua Grup (Tidak Ada Filter)
```env
ALLOWED_GROUPS=
```
atau hapus baris `ALLOWED_GROUPS` dari `.env`

### Contoh 4: Menggunakan Group ID
```env
ALLOWED_GROUPS=120363398239342501@g.us
```

## Verifikasi Filter Bekerja

Setelah restart bot, kirim pesan di grup:

1. **Grup yang diizinkan:**
   - Logs akan muncul: `✅ Group message detected in: Nama Grup (allowed)`
   - Transaksi akan dibuat

2. **Grup yang tidak diizinkan:**
   - Logs akan muncul: `⏭️ Skipping message from non-allowed group: Nama Grup`
   - Transaksi tidak akan dibuat

## Troubleshooting

### Bot Tidak Membaca Pesan dari Grup yang Diizinkan

1. **Cek nama grup di logs:**
   ```bash
   docker-compose logs whatsapp-bot | grep "Groups bot is in"
   ```

2. **Pastikan nama grup sama persis:**
   - Nama grup case-insensitive
   - Tapi harus sama persis (termasuk emoji dan spasi)
   - Contoh: "Happy Family 🥰" bukan "Happy Family"

3. **Cek logs saat mengirim pesan:**
   ```bash
   docker-compose logs -f whatsapp-bot
   ```
   Akan muncul alasan kenapa pesan di-skip

### Mengubah Daftar Grup yang Diizinkan

1. Edit `.env` file
2. Ubah `ALLOWED_GROUPS`
3. Restart bot: `docker-compose restart whatsapp-bot`

### Reset ke Semua Grup

Kosongkan `ALLOWED_GROUPS` di `.env`:
```env
ALLOWED_GROUPS=
```

Kemudian restart bot.

