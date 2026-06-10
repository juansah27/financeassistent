from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app.db import models
from app.db.models import Transaction, TransactionType, RecurringTransaction, RecurringIncome, Budget, Goal, UserCategory
import logging
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

class FinancialQnAService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.user_pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).first()
        self.currency_code = self.user_pref.base_currency_code if self.user_pref else "IDR"

    def process_question(self, question: str) -> str:
        intent = self._detect_intent(question.lower())
        
        # Check for date period in question
        start_date, end_date, period_label = self._parse_period(question.lower())

        # If intent is unknown but we have a date range and "pengeluaran" or just a date range, 
        # assume expense analysis
        if intent == 'unknown':
            if start_date and end_date:
                # If question contains "boros" -> category analysis
                if "boros" in question.lower() or "terbesar" in question.lower():
                     intent = 'analisa_kategori_terbesar'
                elif "tagihan" in question.lower():
                     intent = 'analisa_tagihan_periode'
                else:
                     # Default to expense analysis for the period
                     intent = 'analisa_pengeluaran_bulan_ini'
            elif "pengeluaran" in question.lower():
                # "pengeluaran" without "bulan ini" -> default to month analysis if no date
                intent = 'analisa_pengeluaran_bulan_ini'

        if intent == 'cek_saldo':
            return self.cek_saldo()
        elif intent == 'daily_report':
            return self.generate_daily_report()
        elif intent == 'cek_tagihan_bulan_depan':
            return self.cek_tagihan_bulan_depan()
        elif intent == 'cek_tagihan_sekarang':
            # This is the "Tagihan" without specific period
            return self.cek_tagihan_periode_ini()
        elif intent == 'cek_hutang':
            return self.analisa_hutang_aktif()
        elif intent == 'cek_hutang_telat':
            return self.analisa_hutang_jatuh_tempo()
        elif intent == 'cek_hutang_minggu_ini':
            return self.analisa_hutang_minggu_ini()
        elif intent == 'analisa_tagihan_periode':
            if start_date and end_date:
                return self.analisa_tagihan_periode(start_date, end_date, period_label)
            return self.cek_tagihan_periode_ini() # Fallback to current
        elif intent == 'analisa_pengeluaran_bulan_ini':
            # Use parsed dates if available, otherwise default to "bulan ini"
            if start_date and end_date:
                return self.analisa_pengeluaran(start_date, end_date, period_label)
            else:
                return self.analisa_pengeluaran_bulan_ini()
        elif intent == 'analisa_kategori_terbesar':
            if start_date and end_date:
                return self.analisa_kategori_terbesar(start_date, end_date, period_label)
            return self.analisa_kategori_terbesar()
        elif intent == 'cek_budget_kategori':
            return self.cek_budget_kategori()
        elif intent == 'cek_target_goal':
            return self.cek_target_goal()
        elif intent == 'cek_cashflow':
            return self.cek_cashflow()
        elif intent == 'koreksi_saldo':
            return self.koreksi_saldo(question)
        elif intent == 'help':
            return self.tampilkan_bantuan()
        else:
            return self.tampilkan_bantuan() # Default to help instead of generic message

    def _detect_intent(self, question: str) -> str:
        if "help" in question or "menu" in question or "bantuan" in question:
            return 'help'
        elif "koreksi saldo" in question or "penyesuaian saldo" in question or "set saldo" in question or ("saldo" in question and "sekarang" in question):
            return 'koreksi_saldo'
        elif "saldo" in question or "sisa uang" in question:
            return 'cek_saldo'
        elif "laporan hari ini" in question or "daily report" in question:
            return 'daily_report'
        elif "hutang telat" in question or "hutang lewat" in question or "hutang tunggak" in question:
            return 'cek_hutang_telat'
        elif "hutang minggu ini" in question:
            return 'cek_hutang_minggu_ini'
        elif "hutang" in question:
            return 'cek_hutang'
        elif "tagihan" in question and ("bulan depan" in question or "besok" in question):
            return 'cek_tagihan_bulan_depan'
        elif "tagihan" in question:
            return 'cek_tagihan_sekarang'
        elif "pengeluaran" in question and "bulan ini" in question:
            return 'analisa_pengeluaran_bulan_ini'
        elif "boros" in question or "terbesar" in question:
            return 'analisa_kategori_terbesar'
        elif "budget" in question or "anggaran" in question:
            return 'cek_budget_kategori'
        elif "goal" in question or "target" in question:
            return 'cek_target_goal'
        elif "cashflow" in question or "arus kas" in question:
            return 'cek_cashflow'
        return 'unknown'

    def _format_currency(self, amount: float) -> str:
        return f"Rp {amount:,.0f}"

    def _parse_period(self, question: str):
        """
        Parse date period from question.
        Returns (start_date, end_date, label) or (None, None, None)
        """
        import re
        now = datetime.now()
        
        # 1. Custom Range: "26 januari sampai 31 januari" or "26 jan - 31 jan"
        # Regex to capture: (dd month [year]) ... (dd month [year])
        # We need a month map
        month_map = {
            "januari": 1, "jan": 1, "january": 1, "februari": 2, "feb": 2, "february": 2, 
            "maret": 3, "mar": 3, "march": 3, "april": 4, "apr": 4, 
            "mei": 5, "may": 5, "juni": 6, "jun": 6, "june": 6,
            "juli": 7, "jul": 7, "july": 7, "agustus": 8, "aug": 8, "august": 8, 
            "september": 9, "sep": 9, "sept": 9, "oktober": 10, "okt": 10, "october": 10, "oct": 10,
            "november": 11, "nov": 11, "desember": 12, "des": 12, "dec": 12, "december": 12
        }
        
        # Pattern: digits + space + month_name + optional year
        # Group 1: Day, Group 2: Month, Group 3: Year (optional)
        date_pattern = r"(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?"
        
        # Look for "sampai" or "-" with dates
        # Note: We need to use finditer or careful search because the previous greedy matching might be tricky with optional groups
        # Let's try to match the full range pattern
        range_pattern = f"{date_pattern}.*?(?:sampai|-).*?{date_pattern}"
        range_match = re.search(range_pattern, question)
        
        if range_match:
            try:
                # Groups: 
                # 1: d1, 2: m1, 3: y1 (optional)
                # 4: d2, 5: m2, 6: y2 (optional)
                d1, m1_str, y1_str, d2, m2_str, y2_str = range_match.groups()
                m1 = month_map.get(m1_str.lower())
                m2 = month_map.get(m2_str.lower())
                
                if m1 and m2:
                    current_year = now.year
                    
                    # Determine Year 2
                    year2 = int(y2_str) if y2_str else current_year
                    
                    # Determine Year 1
                    # If y1 is provided, use it.
                    # If y1 is NOT provided, logic:
                    #   - If m1 > m2 (e.g. Dec - Jan), assume y1 is year2 - 1 (unless explicitly said otherwise)
                    #   - Else assume y1 = year2
                    if y1_str:
                        year1 = int(y1_str)
                    else:
                        if m1 > m2 and not y2_str: 
                             # Dec 25 - Jan 5. If year not specified for either, assume cross year logic often implies current context
                             # But standard logic: if y2 is not specified, it's current year. 
                             # if m1 > m2, start date was last year.
                             year1 = year2 - 1
                        elif m1 > m2 and y2_str:
                             # Dec 25 - Jan 5 2026. Then Dec 25 is 2025.
                             year1 = year2 - 1
                        else:
                             year1 = year2

                    start_date = datetime(year1, m1, int(d1))
                    end_date = datetime(year2, m2, int(d2))
                    
                    # Adjust end_date to end of day
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    
                    # Sanity check: if start > end, maybe our year assumption was wrong?
                    # But per logic above, we handled the m1 > m2 case.
                    # Creating the label to show interpreted years
                    label = f"{d1} {m1_str.capitalize()} {year1} - {d2} {m2_str.capitalize()} {year2}"
                    return start_date, end_date, label
            except Exception as e:
                # logger.error(f"Error parsing range: {e}")
                pass

        # 2. Specific Month: "januari 2025" or just "januari"
        for m_name, m_val in month_map.items():
            if m_name in question:
                # Check for year
                year_match = re.search(r"\b20\d{2}\b", question)
                year = int(year_match.group(0)) if year_match else now.year
                
                # Verify this isn't part of the range already matched?
                # The range check is first, so if it returns, we are good.
                # But if range didn't match (e.g. malformed), we might fall here.
                # However, "25 januari" shouldn't trigger "januari" logic if we want strictly full month.
                # But existing logic was loose. Let's keep it.
                
                start_date = datetime(year, m_val, 1)
                if m_val == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    end_date = datetime(year, m_val + 1, 1) - timedelta(seconds=1)
                
                return start_date, end_date, f"{m_name.capitalize()} {year}"

        # 3. Relative periods
        if "bulan lalu" in question:
            # First of previous month
            first_this_month = now.replace(day=1)
            end_date = first_this_month - timedelta(seconds=1)
            start_date = end_date.replace(day=1)
            return start_date, end_date, "Bulan Lalu"
            
        if "minggu ini" in question:
            start_date = now - timedelta(days=now.weekday()) # Monday
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            return start_date, end_date, "Minggu Ini"

        if "minggu lalu" in question:
            # End of previous week was last Sunday
            end_date = (now - timedelta(days=now.weekday() + 1)).replace(hour=23, minute=59, second=59)
            # Start was the Monday before that
            start_date = (end_date - timedelta(days=6)).replace(hour=0, minute=0, second=0)
            return start_date, end_date, "Minggu Lalu"

        return None, None, None

    def _calculate_recurring_occurrences(self, start_date: datetime, end_date: datetime, recurring_items):
        """
        Calculate total amount and detailed occurrences of recurring items within a given date range.
        Handles monthly, weekly, yearly, daily, and custom intervals.
        """
        total_amount = 0
        details = []
        
        for item in recurring_items:
            # item could be RecurringTransaction or RecurringIncome
            current_date = item.next_due_date
            
            # Make sure all datetimes are timezone naive for comparison
            # (assuming they are stored as naive or if start_date/end_date are naive)
            if hasattr(current_date, 'tzinfo') and current_date.tzinfo is not None:
                current_date = current_date.replace(tzinfo=None)
                
            occurrences_count = 0
            # If the item has a remaining_occurrences field and it's not None, keep track of it
            remaining = getattr(item, 'remaining_occurrences', None)
            
            while current_date.date() <= end_date.date():
                # Stop if we have a defined limit and we've reached it
                if remaining is not None and remaining <= 0:
                    break
                    
                if current_date.date() >= start_date.date():
                    total_amount += item.amount
                    occurrences_count += 1
                    
                # If the date is past or equal to today, decrement remaining_occurrences
                # Note: We decrement ONLY if current_date >= today to correctly simulate future payments
                # Or simpler: just decrement it for every cycle we simulate, because we are simulating
                # from next_due_date forward. Since next_due_date is the *next* payment, we decrement for
                # each cycle we process here.
                if remaining is not None:
                    remaining -= 1
                
                # Advance to next due date depending on the recurrence type
                if hasattr(item, 'recurrence_type'):
                    rtype = item.recurrence_type.value if hasattr(item.recurrence_type, 'value') else str(item.recurrence_type)
                    if rtype == "daily":
                        current_date += relativedelta(days=1)
                    elif rtype == "weekly":
                        current_date += relativedelta(weeks=1)
                    elif rtype == "monthly":
                        current_date += relativedelta(months=1)
                    elif rtype == "yearly":
                        current_date += relativedelta(years=1)
                    elif rtype == "custom":
                        interval = item.interval_days if item.interval_days else 30
                        current_date += relativedelta(days=interval)
                    else:
                        break # fallback if unknown
                else:
                    # For RecurringIncome (which might just say Monthly implicitly or have a cycle)
                    current_date += relativedelta(months=1) # Assuming RecurringIncome is monthly

            if occurrences_count > 0:
                name = getattr(item, 'description', None) or getattr(item, 'category', None) or getattr(item, 'name', 'Item')
                details.append(f"* {name}: {self._format_currency(item.amount)} x {occurrences_count} (Total: {self._format_currency(item.amount * occurrences_count)})")
                
        return total_amount, details

    def analisa_tagihan_periode(self, start_date: datetime, end_date: datetime, period_label: str) -> str:
        # Format dates
        start_date_str = start_date.strftime("%d %B %Y")
        end_date_str = end_date.strftime("%d %B %Y")
        
        # 1. Hitung saldo sekarang
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False
        ).scalar()
        
        subtractions = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type.in_([TransactionType.EXPENSE, TransactionType.SAVING, TransactionType.INVESTMENT, TransactionType.DEBT]),
            Transaction.is_deleted == False
        ).scalar()

        income = float(income or 0)
        subtractions = float(subtractions or 0)
        
        current_balance = income - subtractions
        
        # 2. Query SEMUA Recurring Transactions (EXPENSE) yang aktif
        recurring_bills = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id,
            RecurringTransaction.is_active == True,
            RecurringTransaction.type == TransactionType.EXPENSE
        ).all()
        
        # Calculate occurrences in range
        total_bills, bill_items = self._calculate_recurring_occurrences(start_date, end_date, recurring_bills)
        total_bills = float(total_bills)
        
        bill_details = "\n".join(bill_items) if bill_items else ""
        
        # 3. Query Recurring Income di periode tersebut
        recurring_incomes_table = self.db.query(RecurringIncome).filter(
            RecurringIncome.user_id == self.user_id,
            RecurringIncome.status == models.RecurringIncomeStatus.ACTIVE
        ).all()
        
        # Untuk RecurringIncome kita perlu mock next_due_date agar fungsi helper bisa dipakai
        # Karena RecurringIncome di codebase lama mungkin tidak punya next_due_date
        # Asumsikan start of next month jika tidak ada field khusus
        for inc in recurring_incomes_table:
             if not hasattr(inc, 'next_due_date'):
                 # mock it
                 now = datetime.now()
                 inc.next_due_date = now.replace(day=1) + relativedelta(months=1)

        recurring_incomes_trans = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id,
            RecurringTransaction.is_active == True,
            RecurringTransaction.type == TransactionType.INCOME
        ).all()
        
        # Gabungkan semua sumber pemasukan
        income_breakdown_items = []
        projected_income = 0
        
        # Hitung untuk table RecurringIncome
        t_inc1, d_inc1 = self._calculate_recurring_occurrences(start_date, end_date, recurring_incomes_table)
        projected_income += t_inc1
        income_breakdown_items.extend(d_inc1)
        
        # Hitung untuk table RecurringTransaction (INCOME)
        t_inc2, d_inc2 = self._calculate_recurring_occurrences(start_date, end_date, recurring_incomes_trans)
        projected_income += t_inc2
        income_breakdown_items.extend(d_inc2)
        
        income_breakdown = "\n".join(income_breakdown_items) if income_breakdown_items else ""
        
        # Ensure numbers are floats for arithmetic
        projected_income = float(projected_income)
        total_bills = float(total_bills)
        current_balance = float(current_balance)
        
        # 4. Hitung sisa
        remaining = current_balance + projected_income - total_bills
        
        # 5. Tentukan status
        if projected_income > 0:
            ratio = remaining / projected_income
        else:
            ratio = -1 if remaining < 0 else 0
            
        if remaining < 0:
            status = "Tidak Aman"
            analysis = "Anda akan kekurangan dana untuk membayar tagihan di periode ini. Segera cari tambahan dana atau kurangi pengeluaran."
        elif 0 <= ratio <= 0.2:
            status = "Mepet"
            analysis = "Dana cukup tapi sangat pas-pasan (sisa < 20% prediksi pemasukan). Hati-hati dengan pengeluaran tak terduga."
        else:
            status = "Aman"
            analysis = "Keuangan Anda aman untuk membayar tagihan di periode ini."
        
        # Format breakdown dengan newline yang benar
        income_breakdown_formatted = "\n" + income_breakdown if income_breakdown else "\n(Tidak ada pemasukan rutin terjadwal di periode ini)"
        bill_details_formatted = "\n" + bill_details if bill_details else "\n(Tidak ada tagihan terjadwal di periode ini)"
        
        if not bill_items and not income_breakdown_items:
            return f"""*Status: Info*

*Periode:* {start_date_str} s/d {end_date_str} ({period_label})

*Catatan:*
Tidak ada tagihan atau pemasukan rutin yang terjadwal jatuh tempo pada periode ini.

Sistem hanya menyimpan jadwal transaksi berulang terdekat. Tagihan tidak diekstrapolasi karena tidak ada jadwal yang sesuai range waktu tersebut."""
        
        return f"""*Status: {status}*

*Periode:* {start_date_str} s/d {end_date_str} ({period_label})

*Ringkasan Angka:*
• Saldo sekarang: {self._format_currency(current_balance)}

*Prediksi pemasukan periode ini {self._format_currency(projected_income)} berikut detailnya:*{income_breakdown_formatted}

*Total tagihan {period_label} ini: {self._format_currency(total_bills)} berikut detailnya:*{bill_details_formatted}

*Sisa Income setelah bayar tagihan: {self._format_currency(remaining)}*

*Analisa Singkat:*
{analysis}
"""

    def cek_saldo(self) -> str:
        # Logic: Saldo = INCOME - (EXPENSE + SAVING + INVESTMENT + DEBT), TRANSFER tidak dihitung
        
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False
        ).scalar()
        
        subtractions = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type.in_([TransactionType.EXPENSE, TransactionType.SAVING, TransactionType.INVESTMENT, TransactionType.DEBT]),
            Transaction.is_deleted == False
        ).scalar()
        
        income = float(income or 0)
        subtractions = float(subtractions or 0)
        
        balance = income - subtractions
        status = "Aman 🟢" if balance >= 0 else "Tidak Aman 🔴"
        
        return f"""*Status Keuangan: {status}*

*Ringkasan:*
• Pemasukan: *{self._format_currency(income)}*
• Pengeluaran: *{self._format_currency(subtractions)}*
• Saldo Sekarang: *{self._format_currency(balance)}*"""

    def cek_tagihan_bulan_depan(self) -> str:
        # Logic Khusus: Tagihan bulan depan aman atau tidak
        
        # 1. Hitung saldo sekarang (reuse logic)
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False
        ).scalar() or 0
        
        subtractions = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type.in_([TransactionType.EXPENSE, TransactionType.SAVING, TransactionType.INVESTMENT, TransactionType.DEBT]),
            Transaction.is_deleted == False
        ).scalar() or 0
        
        current_balance = float(income) - float(subtractions)
        
        # 2. Hitung total tagihan bulan depan
        now = datetime.now()
        start_next_month = (now.replace(day=1) + relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_next_month = (start_next_month + relativedelta(months=1)) - timedelta(seconds=1)
        
        recurring_bills = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id,
            RecurringTransaction.is_active == True,
            RecurringTransaction.type == TransactionType.EXPENSE
        ).all()
        
        total_bills, bill_items = self._calculate_recurring_occurrences(start_next_month, end_next_month, recurring_bills)
        
        bill_details = "\n".join(bill_items) if bill_items else ""
        
        if not bill_items:
            return "Tagihan bulan depan belum terdaftar. Pastikan Anda mencatat tagihan rutin."
            
        # 3. Hitung prediksi pemasukan bulan depan
        # Ambil dari RecurringIncome table
        recurring_incomes_table = self.db.query(RecurringIncome).filter(
            RecurringIncome.user_id == self.user_id,
            RecurringIncome.status == models.RecurringIncomeStatus.ACTIVE
        ).all()
        for inc in recurring_incomes_table:
             if not hasattr(inc, 'next_due_date'):
                 inc.next_due_date = start_next_month + timedelta(days=5) # mock
        
        # Ambil dari RecurringTransaction table dengan type INCOME
        recurring_incomes_trans = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id,
            RecurringTransaction.is_active == True,
            RecurringTransaction.type == TransactionType.INCOME
        ).all()
        
        # Hitung rata-rata 3 bulan untuk informasi tambahan
        start_this_month = now.replace(day=1, hour=0, minute=0, second=0)
        income_this_month = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_this_month
        ).scalar() or 0
        
        start_last_month = (start_this_month - timedelta(days=1)).replace(day=1)
        end_last_month = start_this_month - timedelta(seconds=1)
        income_last_month = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_last_month,
            Transaction.created_at <= end_last_month
        ).scalar() or 0
        
        start_2months_ago = (start_last_month - timedelta(days=1)).replace(day=1)
        end_2months_ago = start_last_month - timedelta(seconds=1)
        income_2months_ago = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_2months_ago,
            Transaction.created_at <= end_2months_ago
        ).scalar() or 0
        
        avg_3months = (income_this_month + income_last_month + income_2months_ago) / 3
        
        # Gabungkan semua sumber pemasukan
        income_breakdown_items = []
        projected_income = 0
        
        # Tambahkan rata-rata 3 bulan sebagai info
        income_breakdown_items.append(f"* Rata-rata 3 bln terakhir: {self._format_currency(avg_3months)}")
        
        # Dari RecurringIncome table
        t_inc1, d_inc1 = self._calculate_recurring_occurrences(start_next_month, end_next_month, recurring_incomes_table)
        projected_income += t_inc1
        income_breakdown_items.extend(d_inc1)
        
        # Dari RecurringTransaction table (INCOME)
        t_inc2, d_inc2 = self._calculate_recurring_occurrences(start_next_month, end_next_month, recurring_incomes_trans)
        projected_income += t_inc2
        income_breakdown_items.extend(d_inc2)
        
        # Jika tidak ada recurring income sama sekali, gunakan rata-rata
        if projected_income == 0:
            projected_income = avg_3months
        
        income_breakdown = "\n".join(income_breakdown_items) if income_breakdown_items else ""
            
        # 4. Hitung sisa
        remaining = current_balance + projected_income - total_bills
        
        # 5. Tentukan status
        if projected_income > 0:
            ratio = remaining / projected_income
        else:
             ratio = -1 if remaining < 0 else 0 # Edge case
             
        if remaining < 0:
            status = "Tidak Aman"
            status_color = "text-red-500"
            analysis = "Anda akan kekurangan dana untuk membayar tagihan. Segera cari tambahan dana atau kurangi pengeluaran."
        elif 0 <= ratio <= 0.2:
            status = "Mepet"
            status_color = "text-yellow-500"
            analysis = "Dana cukup tapi sangat pas-pasan (sisa < 20% prediksi pemasukan). Hati-hati dengan pengeluaran tak terduga."
        else:
            status = "Aman"
            status_color = "text-green-500"
            analysis = "Keuangan Anda aman untuk membayar tagihan bulan depan."

        # Format breakdown dengan newline yang benar
        income_breakdown_formatted = "\n" + income_breakdown if income_breakdown else ""
        bill_details_formatted = "\n" + bill_details if bill_details else ""
        
        return f"""*Status: {status}*

*Ringkasan Angka:*
• Saldo sekarang: {self._format_currency(current_balance)}

*Prediksi pemasukan bulan depan {self._format_currency(projected_income)} berikut detailnya:*{income_breakdown_formatted}

*Total tagihan bulan depan: {self._format_currency(total_bills)} berikut detailnya:*{bill_details_formatted}

*Sisa Income setelah bayar tagihan: {self._format_currency(remaining)}*

*Analisa Singkat:*
{analysis}

*Rekomendasi:*
{'Tabung sisa dana untuk darurat.' if status == 'Aman' else 'Prioritaskan pembayaran tagihan wajib.'}
"""

    def analisa_pengeluaran_bulan_ini(self) -> str:
        # Default wrapper for backward compatibility or simple calls
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0)
        return self.analisa_pengeluaran(start_of_month, now, "Bulan Ini")

    def analisa_pengeluaran(self, start_date: datetime, end_date: datetime, period_label: str) -> str:
        # Format dates
        start_date_str = start_date.strftime("%d %B %Y")
        end_date_str = end_date.strftime("%d %B %Y")
        
        # Query total transactions
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        ).all()
        
        total_expense = sum(t.amount for t in transactions)
        
        # 1. Group by Category and Sort by Total Amount (DESC)
        category_totals = {}
        for t in transactions:
            category_totals[t.category] = category_totals.get(t.category, 0) + t.amount
        
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        category_detail_items = []
        for cat, amount in sorted_categories[:10]: # Top 10 categories
            category_detail_items.append(f"• {cat}: *{self._format_currency(amount)}*")
        
        category_list_str = "\n".join(category_detail_items) if category_detail_items else "(Tidak ada data kategori)"
        
        # 2. Group Individual Transactions (Fuzzy Matching) and Sort by Amount (DESC)
        import re
        from difflib import SequenceMatcher
        grouped_tx = [] # List of {display_desc, normalized_desc, category, total, count}
        
        for t in transactions:
            # Clean description: strip source info and hashtag keywords (#beli, #bayar, etc.)
            desc = t.description or t.category or "Tanpa keterangan"
            desc = re.sub(r"\s*\(via WhatsApp.*?\)", "", desc)
            desc = re.sub(r"#\w+\s*", "", desc)
            desc = desc.strip()
            
            # Fuzzy match in existing groups
            found_group = None
            for g in grouped_tx:
                if g["category"] == t.category:
                    similarity = SequenceMatcher(None, g["normalized_desc"], desc.lower()).ratio()
                    if similarity >= 0.8:
                        found_group = g
                        break
            
            if found_group:
                found_group["total"] += float(t.amount or 0)
                found_group["count"] += 1
            else:
                grouped_tx.append({
                    "display_desc": desc,
                    "normalized_desc": desc.lower(),
                    "category": t.category,
                    "total": float(t.amount or 0),
                    "count": 1
                })
            
        # Display grouped transactions
        limit = 15
        sorted_groups = sorted(grouped_tx, key=lambda x: x["total"], reverse=True)
        transaction_detail_items = []
        
        for g in sorted_groups[:limit]:
            desc = g["display_desc"]
            # Truncate if still too long
            if len(desc) > 30:
                desc = desc[:27] + "..."
            
            amount_str = f"Rp {float(g['total']):,.0f}".replace(",", ".")
            count_label = f" ({g['count']}x)" if g["count"] > 1 else ""
            transaction_detail_items.append(f"• {desc}: *{amount_str}*{count_label}")
        
        if len(sorted_groups) > limit:
            transaction_detail_items.append(f"• ... dan {len(sorted_groups) - limit} grup transaksi lainnya")
            
        transaction_list_str = "\n".join(transaction_detail_items) if transaction_detail_items else "(Tidak ada transaksi)"
        
        # Get top category for analysis
        top_cat_name = sorted_categories[0][0] if sorted_categories else "-"
        
        return f"""*Status: Analisis Pengeluaran*

*Periode:* {start_date_str} s/d {end_date_str} ({period_label})

*Ringkasan Angka:*
• Total pengeluaran: *{self._format_currency(total_expense)}*
• Jumlah transaksi: *{len(transactions)}*

*Detail Kategori (Terbesar):*
{category_list_str}

*Detail Transaksi (Terbesar):*
{transaction_list_str}

*Analisa Singkat:*
Pengeluaran terbesar Anda ada di kategori *{top_cat_name}*. Total pengeluaran mencapai {self._format_currency(total_expense)} dari {len(transactions)} transaksi.
"""

    def analisa_kategori_terbesar(self, start_date=None, end_date=None, period_label="Bulan Ini") -> str:
        # Logic: TOP 3 kategori pengeluaran terbesar
        if not start_date or not end_date:
            now = datetime.now()
            start_date = now.replace(day=1, hour=0, minute=0, second=0)
            end_date = now
        
        # Format dates
        start_date_str = start_date.strftime("%d %B %Y")
        end_date_str = end_date.strftime("%d %B %Y")
        
        top_categories = self.db.query(
            Transaction.category, func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(3).all()
        
        if not top_categories:
            return "Belum ada data pengeluaran."
            
        details_text = "\n".join([f"• {cat[0]}: *{self._format_currency(cat[1])}*" for cat in top_categories])
        
        return f"""*Status: Analisa Kategori Terbesar (Boros)*

*Periode:* {start_date_str} s/d {end_date_str} ({period_label})

*3 Kategori Pengeluaran Terbesar:*
{details_text}

*Analisa Singkat:*
Fokus penghematan pada kategori *{top_categories[0][0]}* karena memakan porsi terbesar pengeluaran Anda.
"""

    def cek_budget_kategori(self) -> str:
        # Implementasi sederhana untuk cek budget
        # Query budgets table for current month/year
        now = datetime.now()
        budgets = self.db.query(Budget).filter(
            Budget.user_id == self.user_id,
            Budget.year == now.year,
            Budget.month == now.month
        ).all()
        
        if not budgets:
            return "Belum ada anggaran yang diatur untuk bulan ini."
            
        # Calculate actuals
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0)
        category_expenses = {}
        rows = self.db.query(
            Transaction.category, func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_of_month
        ).group_by(Transaction.category).all()
        
        for r in rows:
            category_expenses[r[0]] = r[1]
            
        report_lines = []
        for b in budgets:
            actual = category_expenses.get(b.category, 0)
            status_text = "Over Budget" if actual > b.amount else "Aman"
        report_lines = []
        for b in budgets:
            actual = category_expenses.get(b.category, 0)
            status_text = "Over Budget" if actual > b.amount else "Aman"
            report_lines.append(f"• {b.category}: {self._format_currency(actual)} / {self._format_currency(b.amount)} (*{status_text}*)")
            
        report_text = "\n".join(report_lines)
        return f"""*Status: Budget Report*

*Ringkasan Angka:*
{report_text}

*Analisa Singkat:*
Periksa kategori yang berstatus 'Over Budget' dan kurangi pengeluaran di sana.
"""

    def cek_target_goal(self) -> str:
        goals = self.db.query(Goal).filter(
            Goal.user_id == self.user_id,
            Goal.is_achieved == False
        ).all()
        
        if not goals:
            return "Anda belum memiliki target keuangan aktif."
            
        lines = []
        for g in goals:
            percent = (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
            lines.append(f"• {g.name}: {self._format_currency(g.current_amount)} / {self._format_currency(g.target_amount)} ({percent:.1f}%)")
            
        lines_text = "\n".join(lines)
        return f"""*Status: Goals Progress*

*Ringkasan Angka:*
{lines_text}

*Analisa Singkat:*
Terus menabung untuk mencapai target Anda!
"""

    def cek_cashflow(self) -> str:
        # Pemasukan vs Pengeluaran bulan ini
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0)
        
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_of_month
        ).scalar() or 0
        
        expense = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_of_month
        ).scalar() or 0
        
        surplus = income - expense
        status = "Positif" if surplus >= 0 else "Negatif"
        
        return f"""*Status: Cashflow {status}*

*Ringkasan Angka:*
• Pemasukan Bulan Ini: {self._format_currency(income)}
• Pengeluaran Bulan Ini: {self._format_currency(expense)}
• Surplus/Defisit: {self._format_currency(surplus)}

*Analisa Singkat:*
{'Cashflow Anda positif, bagus!' if surplus >= 0 else 'Cashflow negatif, artinya pengeluaran lebih besar dari pemasukan bulan ini.'}
"""

    def generate_daily_report(self) -> str:
        from app.services.report_generator import generate_daily_report
        return generate_daily_report(self.db, self.user_id)

    def cek_tagihan_periode_ini(self) -> str:
        # Get start/end of current month
        now = datetime.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # End of current month
        if now.month == 12:
            end_date = now.replace(year=now.year + 1, month=1, day=1)
        else:
            end_date = now.replace(month=now.month + 1, day=1)
            
        return self.analisa_tagihan_periode(start_date, end_date, "Bulan Ini")

    def analisa_hutang_aktif(self) -> str:
        from app.db import crud_new_features
        debts = crud_new_features.get_debts(self.db, self.user_id, active_only=True)
        
        if not debts:
            return "Anda tidak memiliki hutang aktif saat ini. Bagus! 🌟"
            
        total_remaining = sum(d.remaining_amount for d in debts)
        
        res = f"""*Status: Hutang Aktif*
*Total Kewajiban: {self._format_currency(total_remaining)}*

*Daftar Hutang:*
"""
        for d in debts:
            due_str = f" (Jatuh tempo: {d.due_date.strftime('%d/%m/%Y')})" if d.due_date else ""
            res += f"• {d.creditor}: {self._format_currency(d.remaining_amount)}{due_str}\n"
            
        return res

    def analisa_hutang_jatuh_tempo(self) -> str:
        from app.db import crud_new_features
        debts = crud_new_features.get_debts(self.db, self.user_id, active_only=True)
        now = datetime.now()
        overdue = [d for d in debts if d.due_date and d.due_date < now]
        
        if not overdue:
            return "Tidak ada hutang yang jatuh tempo saat ini. Aman! ✅"
            
        total_overdue = sum(d.remaining_amount for d in overdue)
        
        res = f"""*Status: ⚠️ Terlambat Bayar*
*Total Menunggak: {self._format_currency(total_overdue)}*

*Detail Tunggakan:*
"""
        for d in overdue:
            days = (now - d.due_date).days
            res += f"• {d.creditor}: {self._format_currency(d.remaining_amount)} (Terlambat {days} hari)\n"
            
        return res

    def analisa_hutang_minggu_ini(self) -> str:
        from app.db import crud_new_features
        debts = crud_new_features.get_debts(self.db, self.user_id, active_only=True)
        now = datetime.now()
        next_week = now + timedelta(days=7)
        upcoming = [d for d in debts if d.due_date and now <= d.due_date <= next_week]
        
        if not upcoming:
            return "Tidak ada hutang yang harus dibayar minggu ini. 👍"
            
        total_upcoming = sum(d.remaining_amount for d in upcoming)
        
        res = f"""*Status: Tagihan Hutang Minggu Ini*
*Total Harus Dibayar: {self._format_currency(total_upcoming)}*

*Jadwal Bayar:*
"""
        for d in upcoming:
            days_left = (d.due_date - now).days
            due_label = "Hari ini" if days_left == 0 else f"{days_left} hari lagi"
            res += f"• {d.creditor}: {self._format_currency(d.remaining_amount)} ({due_label})\n"
            
        return res

    def koreksi_saldo(self, question: str) -> str:
        from app.utils import parse_amount
        from app.db.crud import create_transaction
        
        target_amount = parse_amount(question)
        if target_amount is None:
            return "Maaf, saya tidak dapat mendeteksi nominal untuk koreksi saldo. Pastikan formatnya benar, contoh: *? Koreksi saldo 500.000*"

        # Calculate current balance (comprehensive)
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False
        ).scalar() or 0
        
        subtractions = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == self.user_id,
            Transaction.type.in_([TransactionType.EXPENSE, TransactionType.SAVING, TransactionType.INVESTMENT, TransactionType.DEBT]),
            Transaction.is_deleted == False
        ).scalar() or 0
        
        current_balance = float(income) - float(subtractions)
        diff = target_amount - current_balance
        
        if abs(diff) < 1:
            return f"Saldo Anda sudah sesuai dengan nominal {self._format_currency(target_amount)}."
            
        if diff > 0:
            # Create Income Adjustment
            create_transaction(
                db=self.db,
                user_id=self.user_id,
                transaction_type=TransactionType.INCOME,
                amount=diff,
                category="Penyesuaian Saldo",
                description="Koreksi saldo via WhatsApp"
            )
            msg = f"Berhasil menambah saldo sebesar {self._format_currency(diff)}."
        else:
            # Create Expense Adjustment
            create_transaction(
                db=self.db,
                user_id=self.user_id,
                transaction_type=TransactionType.EXPENSE,
                amount=abs(diff),
                category="Penyesuaian Saldo",
                description="Koreksi saldo via WhatsApp"
            )
            msg = f"Berhasil mengurangi saldo sebesar {self._format_currency(abs(diff))}."
            
        return f"""✅ *Koreksi Saldo Berhasil*
        
• Saldo Sebelumnya: {self._format_currency(current_balance)}
• {msg}
• Saldo Sekarang: *{self._format_currency(target_amount)}*
"""

    def tampilkan_bantuan(self) -> str:
        return """*🤖 Panduan Perintah Bot Keuangan*

*1. Tanya Jawab (Gunakan awalan ?)*
• *? Saldo*: Cek sisa uang saat ini
• *? Pengeluaran*: Analisa pengeluaran bulan ini
• *? Pengeluaran [periode]*: Cek periode tertentu (cth: *? pengeluaran minggu lalu* atau *? pengeluaran 1 jan - 15 jan*)
• *? Laporan hari ini*: Laporan ringkasan hari ini
• *? Tagihan*: Cek tagihan/pembayaran rutin bulan ini
• *? Tagihan bulan depan*: Cek tagihan/pembayaran rutin bulan depan
• *? Boros*: Kategori pengeluaran terbesar
• *? Budget*: Status anggaran vs pengeluaran
• *? Goal*: Progres target tabungan
• *? Cashflow*: Arus kas bulan ini

*2. Manajemen Hutang & Adjustment*
• *? Hutang*: Daftar semua hutang aktif
• *? Hutang telat*: Hutang yang sudah jatuh tempo
• *? Hutang minggu ini*: Hutang yang harus dibayar minggu ini
• *? Koreksi saldo*: Sesuaikan saldo sistem (cth: *? koreksi saldo 500rb*)

*3. Laporan & Dashboard*
• *laporan hari ini*: Ringkasan harian lengkap
• *cek budget*: Status budget bulan ini

*4. Pencatatan Transaksi*
• *Teks Bebas*: Ketik nominal dan barang (cth: Makan 25k)
• *Transaksi Rutin*: Tambahkan hashtag untuk pengeluaran/pemasukan rutin (cth: Netflix 150k #recurring #monthly, atau Nabung 50k #recurring #tiap 14 hari)
• *Scan Struk*: Kirim foto struk belanja

_Tip: Gunakan awalan "?" untuk bertanya langsung ke asisten cerdas saya._
"""
