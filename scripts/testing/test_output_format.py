"""
Test script untuk melihat output format tagihan bulan depan
"""

# Simulasi output
status = "Aman"
current_balance = 1845436
projected_income = 4400000
total_bills = 2070989
remaining = 4174447
analysis = "Keuangan Anda aman untuk membayar tagihan bulan depan."

def format_currency(amount):
    return f"Rp {amount:,.0f}"

# Simulasi breakdown
income_breakdown = """* Rata-rata 3 bulan: Rp 0, Rp 10,388,561, Rp 3,044,142
* Gaji FlexoFast (Sella): Rp 4,400,000"""

bill_details = """* Kredivo Uang Kuliah semester 5: Rp 374,960
* tiktok paylater moel deal body lotion and face wash: Rp 129,892
* Wifi om Dwi: Rp 200,000
* Upah Nanny Gavin: Rp 1,000,000"""

# Format breakdown dengan newline yang benar
income_breakdown_formatted = "\n" + income_breakdown if income_breakdown else ""
bill_details_formatted = "\n" + bill_details if bill_details else ""

output = f"""*Status: {status}*

*Ringkasan Angka:*
• Saldo sekarang: {format_currency(current_balance)}

*Prediksi pemasukan bulan depan {format_currency(projected_income)} berikut detailnya:*{income_breakdown_formatted}

*Total tagihan bulan depan: {format_currency(total_bills)} berikut detailnya:*{bill_details_formatted}

*Sisa Income setelah bayar tagihan: {format_currency(remaining)}*

*Analisa Singkat:*
{analysis}

*Rekomendasi:*
{'Tabung sisa dana untuk darurat.' if status == 'Aman' else 'Prioritaskan pembayaran tagihan wajib.'}
"""

print(output)
print("\n" + "="*50)
print("Output untuk WhatsApp:")
print("="*50)
print(repr(output))
