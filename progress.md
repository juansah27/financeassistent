# Progress Log

## 2026-05-28
- Rekonsiliasi saldo Ayah/Bunda selesai: saldo account real diset sesuai info terbaru dan total transaksi/accounting disamakan dengan total account aktif
- Update account: Ayah ATM BCA `Rp4.435.473`, Ayah Dompet `Rp722.000`, Bunda Dompet `Rp110.000`
- Adjustment transaksi dibuat dengan `account_id = NULL` agar tidak mengubah saldo account: Ayah `Adjustment Income Rp5.866.920,11`, Bunda `Adjustment Income Rp704.500`
- Verifikasi DB: Ayah total account `Rp5.209.893` = total transaksi `Rp5.209.893`; Bunda total account `Rp122.844` = total transaksi `Rp122.844`; selisih masing-masing `Rp0`
- Ditambah command bantuan WhatsApp: `!help`, `help`, `bantuan`, dan `menu`
- Help command ditangani langsung di Node bot agar tidak masuk parser transaksi dan tidak tercatat Rp0
- Multi-line message aman: baris help command dibalas menu bantuan dan baris lain tetap diproses
- Backend webhook diberi fallback help command kalau command tetap sampai ke FastAPI
- Format bantuan hutang/tagihan/paylater dirapikan agar lebih mudah dibaca di WhatsApp
- File yang diubah: `whatsapp-bot/handlers/command.js`, `whatsapp-bot/handlers/message.js`, `app/routes/whatsapp.py`
- Validasi selesai: `node --check` untuk file bot, `python3 -m py_compile app/routes/whatsapp.py`, restart `finance_web` dan `finance_whatsapp_bot`, test webhook `!help` sukses
- Catatan: log `sync-groups 404` masih muncul tapi unrelated dan sudah ada sebelumnya

## 2026-05-26
- Hermes profile finance: perbaikan format pesan Telegram
- Disepakati aturan format baru: bullet list (`• item | info`) untuk 90% pesan, code block hanya untuk data tabular (20+ transaksi)
- Format terlarang: `═══` borders, `****` bold mentah, ASCII box, markdown table
- Format rules disimpan ke memory + skill profile finance
- Finance gateway di-restart agar perubahan langsung apply
- Tidak ada perubahan kode di project ini — perubahan ada di konfigurasi Hermes profile
