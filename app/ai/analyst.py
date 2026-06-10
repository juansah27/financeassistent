from openai import OpenAI
import os

def get_openai_client():
    """Get OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def analyze_finances(stats: dict) -> str:
    """Generate financial analysis in Indonesian"""
    
    income = stats.get("income", 0)
    expenses = stats.get("expenses", 0)
    balance = stats.get("balance", 0)
    daily_balance = stats.get("daily_balance")
    total_balance = stats.get("total_balance")
    category_breakdown = stats.get("category_breakdown", {})
    period = stats.get("period", "monthly")
    
    period_text = "bulan ini" if period == "monthly" else "hari ini" if period == "daily" else "minggu ini"
    
    prompt = f"""Sebagai asisten keuangan keluarga, analisis data keuangan {period_text} dan berikan insight singkat dalam bahasa Indonesia (maksimal 3 kalimat).
    Gunakan gaya bahasa yang ramah, santai, tapi tetap profesional dan memotivasi.

    DATA:
    - Pemasukan: Rp {income:,.0f}
    - Pengeluaran: Rp {expenses:,.0f}"""
    
    if daily_balance is not None:
        prompt += f"\n    - Saldo Harian: Rp {daily_balance:,.0f}"
    if total_balance is not None:
        prompt += f"\n    - Total Saldo Akumulasi: Rp {total_balance:,.0f}"
    else:
        prompt += f"\n    - Sisa: Rp {balance:,.0f}"
        
    if category_breakdown:
        prompt += f"\n\n    Rincian pengeluaran per kategori:\n    {chr(10).join(f'- {cat}: Rp {amt:,.0f}' for cat, amt in category_breakdown.items())}"
    
    prompt += "\n\nBerikan analisis yang spesifik berdasarkan angka tersebut, bukan kalimat generik."

    client = get_openai_client()
    if not client:
        # Fallback analysis
        if (daily_balance is not None and daily_balance < 0) or balance < 0:
            return f"Pengeluaran {period_text} melebihi pemasukan. Coba cek lagi daftar transaksi, mana yang bisa dikurangi ya."
        return f"Kondisi keuangan {period_text} terpantau aman. Pertahankan pola spending yang bijak!"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Anda adalah asisten keuangan keluarga Indonesia yang cerdas dan suportif."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI Error in analyze_finances: {e}")
        return "Gagal mendapatkan analisis AI, tapi secara umum kondisi keuanganmu masih terpantau oleh sistem."

def get_financial_advice(user_data: dict) -> str:
    """Generate strategic financial advice to 'get rich' and improve financial health"""
    
    monthly_stats = user_data.get("monthly_stats", {})
    assets = user_data.get("assets", [])
    debts = user_data.get("debts", [])
    budgets = user_data.get("budgets", [])
    
    # Format asset info
    asset_info = "\n".join([f"- {a['name']} ({a['type']}): Rp {a['total_value']:,.0f}" for a in assets]) if assets else "Belum ada data aset."
    
    # Format debt info
    debt_info = "\n".join([f"- {d.creditor}: Rp {d.remaining_amount:,.0f} (Cicilan: Rp {d.installment_amount or 0:,.0f})" for d in debts]) if debts else "Tidak ada hutang aktif."
    
    # Format budget info
    over_budget = [b for b in budgets if b.get('percentage', 0) > 100]
    budget_info = f"Kategori jebol: {', '.join([b['name'] for b in over_budget])}" if over_budget else "Semua budget aman."
    
    prompt = f"""Sebagai konsultan keuangan profesional, berikan saran strategis agar keluarga ini bisa mencapai kebebasan finansial ('cepat kaya' secara sehat).
    Berikan 3 poin saran yang paling mendesak dan berdampak besar berdasarkan data mereka.

    KONDISI SAAT INI:
    - Pemasukan Bulanan: Rp {monthly_stats.get('income', 0):,.0f}
    - Pengeluaran Bulanan: Rp {monthly_stats.get('expenses', 0):,.0f}
    - Sisa (Saving Capacity): Rp {monthly_stats.get('balance', 0):,.0f}
    
    ASET:
    {asset_info}
    
    HUTANG:
    {debt_info}
    
    STATUS BUDGET:
    {budget_info}

    Gunakan bahasa Indonesia yang inspiratif dan berikan langkah konkret (misal: 'Alokasikan sisa Rp 2jt ke Reksadana' atau 'Lunasi hutang bank dulu')."""

    client = get_openai_client()
    if not client:
        return "Saran sederhana: Prioritaskan pelunasan hutang dengan bunga tinggi, lalu bangun dana darurat sebesar 6x pengeluaran bulanan sebelum mulai berinvestasi."
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Anda adalah Financial Planner profesional yang membantu keluarga mencapai kekayaan lewat manajemen uang yang bijak."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=400
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI Error in get_financial_advice: {e}")
        return "Fokuslah pada menabung minimal 20% dari pendapatan dan hindari hutang konsumtif untuk membangun kekayaan jangka panjang."

