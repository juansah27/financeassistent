# Panduan Penggunaan Bot Keuangan

Bot ini dirancang untuk membantu Anda mencatat transaksi, memantau keuangan, dan mengelola hutang melalui WhatsApp. Berikut adalah kemampuan lengkap dan format yang didukung.

## 1. Tanya Jawab Keuangan (Q&A)
Gunakan awalan **`?`** atau kata **`tanya`** untuk menanyakan status keuangan Anda.

| Perintah | Deskripsi | Contoh |
| :--- | :--- | :--- |
| **`? Saldo`** | Cek sisa saldo saat ini (Pemasukan - Pengeluaran). | `? Saldo` |
| **`? Tagihan`** | Cek tagihan rutin yang akan jatuh tempo bulan depan. | `? Tagihan`, `? Tagihan bulan depan` |
| **`? Tagihan [Periode]`** | Cek tagihan dalam rentang tanggal tertentu. | `? Tagihan Jan - Feb`, `? Tagihan minggu ini` |
| **`? Pengeluaran`** | Analisa total pengeluaran bulan ini. | `? Pengeluaran`, `? Pengeluaran bulan ini` |
| **`? Pengeluaran [Periode]`** | Analisa pengeluaran dalam periode tertentu. | `? Pengeluaran kemarin`, `? Pengeluaran 1 Jan - 15 Jan` |
| **`? Boros`** | Melihat kategori pengeluaran terbesar (Top 3). | `? Boros`, `? Apa yang paling boros`, `? Terbesar` |
| **`? Budget`** | Cek status anggaran (Over budget atau Aman). | `? Budget`, `? Anggaran` |
| **`? Goal`** | Cek progres target keuangan/tabungan. | `? Goal`, `? Target` |
| **`? Cashflow`** | Cek arus kas (Surplus/Defisit) bulan ini. | `? Cashflow`, `? Arus kas` |
| **`? Koreksi Saldo`** | Menyesuaikan saldo sistem dengan nominal asli. | `? Koreksi saldo 500rb`, `? Saldo sekarang 1jt` |
| **`? Help`** | Menampilkan menu bantuan. | `? Help`, `? Menu`, `? Bantuan` |

> **Tips:** Bot cukup pintar untuk memahami variasi pertanyaan seperti "sisa duit", "tagihan bulan depan apa aja", "pengeluaran 2 hari terakhir".

## 2. Manajemen Hutang
Perintah khusus untuk memantau hutang piutang tanpa awalan `?`.

| Perintah | Deskripsi |
| :--- | :--- |
| **`hutang`** / **`tagihan`** | Menampilkan daftar **semua hutang aktif** beserta sisa dan statusnya. |
| **`hutang telat`** | Menampilkan daftar hutang yang sudah **jatuh tempo** (telat bayar). |
| **`hutang minggu ini`** | Menampilkan daftar hutang yang harus dibayar **minggu ini**. |

## 3. Pencatatan Transaksi (Teks)
Anda bisa mencatat transaksi hanya dengan mengirim pesan teks biasa. Bot akan mencoba mendeteksi angka dan konteks.

*   **Format Bebas:** Kirim pesan berisi nominal dan keterangan.
    *   *Contoh:* "Beli makan siang 25000"
    *   *Contoh:* "Bayar listrik 500.000"
    *   *Contoh:* "Gaji masuk 10.000.000"

*   **Laporan:** Kata kunci tertentu akan menampilkan laporan singkat.
    *   *Kata Kunci:* "laporan hari ini", "share report", "info keuangan".

## 4. Scan Struk & Gambar (OCR)
Bot dapat membaca gambar struk, bukti transfer, atau mutasi rekening.

**Cara Penggunaan:**
1.  Kirim gambar ke bot (Foto langsung atau dari galeri).
2.  (Opsional) Tambahkan caption jika perlu.
3.  Bot akan memproses dan membalas dengan detail transaksi yang diekstrak.

**Format Gambar yang Didukung:**
*   **JPG / JPEG**
*   **PNG**

**Data yang Bisa Dibaca:**
*   **Total Nominal:** Bot mencari "Total", "Jumlah", "Transfer", atau kombinasi Nominal + Biaya Admin.
*   **Tanggal:** Mencari format tanggal (DD/MM/YYYY atau YYYY-MM-DD).
*   **Nama Merchant/Bank:** Mendeteksi nama bank (BCA, Mandiri, dll) atau nama toko.
*   **Keterangan:** Mengambil deskripsi transaksi.
*   **Tujuan Transaksi:** Jika ada field "TUJUAN TRANSAKSI" pada struk.

> **Catatan:** Akurasi pembacaan tergantung pada kualitas gambar. Pastikan gambar jelas, tidak buram, dan pencahayaan cukup.

## 5. Konfirmasi
Bot mungkin meminta konfirmasi sederhana:
*   `ya`, `ok`, `y` (Setuju)
*   `tidak`, `no`, `n`, `batal` (Batal)
