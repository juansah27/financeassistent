"""
WhatsApp Daily Financial Report Generator
"""
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.db import crud, crud_extended, models
from app.db.models import Transaction, TransactionType, Budget, User, UserPreference
from app.ai import analyst
from app.ai.classifier import clean_description
from typing import Dict, List


def _fmt_rp(amount: float) -> str:
    """Format full Rupiah with Indonesian separators."""
    return f"Rp {float(amount or 0):,.0f}".replace(',', '.')


def _fmt_rp_k(amount: float) -> str:
    """Compact Rupiah format for WhatsApp report sections."""
    amount = float(amount or 0)
    if abs(amount) >= 1_000_000:
        value = amount / 1_000_000
        return f"Rp{value:.1f}jt".replace('.0jt', 'jt').replace('.', ',')
    return f"Rp{round(amount / 1000):,.0f}k".replace(',', '.')


def _get_report_scope_users(db: Session, user_id: int = None) -> List[User]:
    """For a scheduled family report, include users in the same family."""
    if not user_id:
        return db.query(User).order_by(User.id).all()

    owner = db.query(User).filter(User.id == user_id).first()
    if owner and owner.family_id:
        return db.query(User).filter(User.family_id == owner.family_id).order_by(User.id).all()
    return [owner] if owner else []


def _get_budget_period(today, start_day: int):
    """Return (period_start, budget_year, budget_month) using custom reset day convention."""
    start_day = start_day or 1
    if today.day >= start_day:
        period_start = today.replace(day=start_day)
        if today.month < 12:
            budget_month = today.month + 1
            budget_year = today.year
        else:
            budget_month = 1
            budget_year = today.year + 1
    else:
        prev_month_last = today.replace(day=1) - timedelta(days=1)
        period_start = prev_month_last.replace(day=start_day)
        budget_month = today.month
        budget_year = today.year
    return period_start, budget_year, budget_month


def _format_budget_compact_section(db: Session, scope_user_ids: List[int], today) -> str:
    """Compact JEBOL/MENIPIS budget section, grouped by user."""
    lines = ["📊 *Budget* 🔴"]
    any_budget = False

    user_names = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(scope_user_ids)).all()
    } if scope_user_ids else {}

    for uid in scope_user_ids:
        pref = db.query(UserPreference).filter(UserPreference.user_id == uid).first()
        start_day = pref.start_of_month if pref and pref.start_of_month else 1
        period_start, budget_year, budget_month = _get_budget_period(today, start_day)
        period_start_naive = datetime.combine(period_start, datetime.min.time())

        budgets = db.query(Budget).filter(
            Budget.user_id == uid,
            Budget.year == budget_year,
            Budget.month == budget_month
        ).all()
        if not budgets:
            continue

        any_budget = True
        rows = []
        safe = []
        for b in budgets:
            spent = db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == uid,
                Transaction.is_deleted == False,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.category == b.category,
                func.timezone('Asia/Jakarta', Transaction.created_at) >= period_start_naive,
                ~Transaction.category.ilike('%adjustment%')
            ).scalar() or 0
            budget_amount = float(b.amount or 0)
            spent_amount = float(spent or 0)
            pct = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
            rows.append((pct, b.category, spent_amount, budget_amount))

        hot_rows = [r for r in rows if r[0] >= 80]
        safe_rows = [r for r in rows if 0 < r[0] < 80]
        hot_rows.sort(reverse=True, key=lambda x: x[0])
        safe_rows.sort(reverse=True, key=lambda x: x[0])

        user_label = user_names.get(uid, f"User {uid}")
        lines.append(f"👤 *{user_label}*")
        if hot_rows:
            for pct, category, spent, budget in hot_rows[:8]:
                status = "🚨JEBOL" if pct > 100 else "⚠️MENIPIS"
                lines.append(f"• {category} {_fmt_rp_k(spent)}/{_fmt_rp_k(budget)} ({pct:.0f}%) {status}")
        else:
            lines.append("• Belum ada kategori menipis/jebol 🟢")

        if safe_rows:
            safe_text = ", ".join(f"{cat} {pct:.0f}%" for pct, cat, _, _ in safe_rows[:6])
            lines.append(f"• Sisanya aman 🟢 ({safe_text})")

    if not any_budget:
        return "📊 *Budget*\n• Budget periode ini belum diset"
    return "\n".join(lines)


def _format_assets_section(db: Session, scope_user_ids: List[int]) -> str:
    assets = db.query(models.Asset).filter(
        models.Asset.user_id.in_(scope_user_ids),
        models.Asset.is_active == True
    ).order_by(models.Asset.current_value.desc()).all() if scope_user_ids else []

    if not assets:
        return "💎 *Assets*\n• Belum ada aset aktif"

    user_map = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_({a.user_id for a in assets})).all()
    }
    lines = ["💎 *Assets*"]
    total = 0
    for asset in assets[:10]:
        value = float(asset.current_value or 0)
        total += value
        qty = ""
        if asset.quantity and asset.unit:
            qty = f" | {float(asset.quantity):g} {asset.unit}"
        owner = user_map.get(asset.user_id, f"User {asset.user_id}")
        asset_type = asset.asset_type.value if asset.asset_type else "Aset"
        lines.append(f"• {asset.name} | {_fmt_rp_k(value)} | {asset_type}{qty} | {owner}")
    if len(assets) > 10:
        lines.append(f"• +{len(assets)-10} aset lain")
    lines.append(f"• Total aset: *{_fmt_rp_k(sum(float(a.current_value or 0) for a in assets))}*")
    return "\n".join(lines)


def _format_debts_section(db: Session, scope_user_ids: List[int], tz: ZoneInfo) -> str:
    debts = db.query(models.Debt).filter(
        models.Debt.is_active == True,
        (
            models.Debt.user_id.in_(scope_user_ids)
            | models.Debt.creditor_user_id.in_(scope_user_ids)
            | models.Debt.debtor_user_id.in_(scope_user_ids)
        )
    ).order_by(models.Debt.due_date.asc().nullslast(), models.Debt.remaining_amount.desc()).all() if scope_user_ids else []

    if not debts:
        return "🏦 *Debts/Hutang*\n• Belum ada hutang aktif"

    linked_user_ids = set(scope_user_ids)
    for d in debts:
        if d.creditor_user_id:
            linked_user_ids.add(d.creditor_user_id)
        if d.debtor_user_id:
            linked_user_ids.add(d.debtor_user_id)
    user_map = {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(linked_user_ids)).all()
    }

    lines = ["🏦 *Debts/Hutang*"]
    total = 0
    for debt in debts[:10]:
        remaining = float(debt.remaining_amount or 0)
        total += remaining
        if debt.creditor_user_id or debt.debtor_user_id:
            debtor = user_map.get(debt.debtor_user_id, "?") if debt.debtor_user_id else user_map.get(debt.user_id, "?")
            creditor = user_map.get(debt.creditor_user_id, debt.creditor or "?")
            name = f"{debtor} → {creditor}"
        else:
            name = debt.name or debt.creditor or "Hutang"
        due = ""
        if debt.due_date:
            due = f" | due {debt.due_date.astimezone(tz).strftime('%d/%m')}"
        installment = ""
        if debt.installment_amount:
            installment = f" | cicilan {_fmt_rp_k(float(debt.installment_amount))}"
        lines.append(f"• {name} | {_fmt_rp_k(remaining)}{installment}{due}")
    if len(debts) > 10:
        lines.append(f"• +{len(debts)-10} hutang lain")
    lines.append(f"• Total hutang: *{_fmt_rp_k(sum(float(d.remaining_amount or 0) for d in debts))}*")
    return "\n".join(lines)


def generate_daily_report(db: Session, user_id: int = None) -> str:
    """
    Generate daily financial report for WhatsApp
    """
    # Get today's date range (Indonesia timezone)
    tz = ZoneInfo("Asia/Jakarta")
    today = datetime.now(tz).date()
    start_of_day_naive = datetime.combine(today, datetime.min.time())
    end_of_day_naive = datetime.combine(today, datetime.max.time())

    scope_users = _get_report_scope_users(db, user_id)
    scope_user_ids = [u.id for u in scope_users]
    user_map = {u.id: u.username for u in scope_users}
    
    # Query today's transactions using timezone conversion
    query = db.query(Transaction).filter(
        func.timezone('Asia/Jakarta', Transaction.created_at) >= start_of_day_naive,
        func.timezone('Asia/Jakarta', Transaction.created_at) <= end_of_day_naive,
        Transaction.is_deleted == False
    )
    
    if scope_user_ids:
        query = query.filter(Transaction.user_id.in_(scope_user_ids))
    elif user_id:
        query = query.filter(Transaction.user_id == user_id)
    
    transactions = query.all()
    visible_transactions = [
        t for t in transactions
        if not (t.category and "adjustment" in t.category.lower())
    ]

    # Calculate today's visible totals (exclude adjustments so totals match listed rows)
    total_income = float(sum(t.amount for t in visible_transactions if t.type == TransactionType.INCOME) or 0)
    total_expense = float(sum(t.amount for t in visible_transactions if t.type == TransactionType.EXPENSE) or 0)
    daily_balance = total_income - total_expense
    
    # Calculate cumulative balance
    all_query = db.query(Transaction).filter(Transaction.is_deleted == False)
    if scope_user_ids:
        all_query = all_query.filter(Transaction.user_id.in_(scope_user_ids))
    elif user_id:
        all_query = all_query.filter(Transaction.user_id == user_id)
    all_transactions = all_query.all()
    cumulative_income = float(sum(t.amount for t in all_transactions if t.type == TransactionType.INCOME) or 0)
    cumulative_expense = float(sum(t.amount for t in all_transactions if t.type == TransactionType.EXPENSE) or 0)
    total_balance = cumulative_income - cumulative_expense
    
    # Category breakdown for expenses
    category_breakdown = {}
    for t in visible_transactions:
        if t.type == TransactionType.EXPENSE:
            cat_name = t.category or 'Lainnya'
            category_breakdown[cat_name] = category_breakdown.get(cat_name, 0) + float(t.amount or 0)
    
    # AI Insight
    stats = {
        "income": total_income,
        "expenses": total_expense,
        "daily_balance": daily_balance,
        "total_balance": total_balance,
        "category_breakdown": category_breakdown
    }
    
    try:
        insight = _generate_daily_insight(stats, len(visible_transactions))
    except Exception:
        insight = _get_fallback_insight(daily_balance, total_expense, total_income, category_breakdown, total_balance)
    
    # Format report
    day_name_id = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }.get(today.strftime('%A'), today.strftime('%A'))
    
    date_str = today.strftime('%d %B %Y')
    month_id = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    date_str = f"{today.day} {month_id[today.month-1]} {today.year}"

    # Filter only expense transactions (skip adjustment)
    expense_tx = [t for t in transactions
                  if t.type == TransactionType.EXPENSE
                  and not (t.category and "adjustment" in t.category.lower())]
    sorted_tx = sorted(expense_tx, key=lambda t: t.created_at)
    
    # Group by user
    user_tx_groups = {}
    for t in sorted_tx:
        uid = t.user_id or 0
        user_tx_groups.setdefault(uid, []).append(t)
    
    report = f"📅 Laporan Keuangan {day_name_id}, {date_str}\n\n"
    
    for uid in sorted(user_tx_groups.keys()):
        username = user_map.get(uid, 'Tidak diketahui')
        tx_list = user_tx_groups[uid]
        total_user = sum(float(t.amount or 0) for t in tx_list)
        total_user_str = f"Rp {total_user:,.0f}".replace(',', '.')
        
        report += f"Transaksi {username} :\n"
        for t in tx_list:
            t_time = t.created_at.astimezone(tz).strftime('%H:%M')
            amount_str = f"Rp {float(t.amount):,.0f}".replace(',', '.')
            desc = clean_description(t.raw_input or t.description or t.category or 'Tanpa keterangan')
            report += f"- {t_time} | `{amount_str}` | {desc} | {username} | {t.category or 'Lain-lain'}\n"
        report += f"\n💸 Total Pengeluaran {username} Hari Ini: `{total_user_str}`\n\n"
    
    report += f"📝 Total Transaksi: {len(sorted_tx)}"
    
    # Gold price & exchange rate section
    try:
        from sqlalchemy import text as sqltext
        rows = db.execute(
            sqltext("SELECT price_per_gram, usd_to_idr, gbp_to_idr, created_at FROM gold_prices ORDER BY created_at DESC LIMIT 2")
        ).all()
        if rows:
            # Latest row
            latest = rows[0]
            r_date = latest[3].astimezone(tz).strftime('%d/%m')
            # Previous row for comparison
            prev = rows[1] if len(rows) > 1 else None

            def arrow(current, previous):
                if previous is None or previous == 0:
                    return ""
                diff_pct = ((current - previous) / previous) * 100
                diff_pct_str = f"{abs(diff_pct):.1f}%"
                if current > previous:
                    return f" Naik +{diff_pct_str}"
                elif current < previous:
                    return f" Turun -{diff_pct_str}"
                else:
                    return " Tetap"

            emas_arrow = arrow(float(latest[0]), float(prev[0]) if prev and prev[0] is not None else None)
            report += f"\n\n🥇 *Emas Spot:* Rp {float(latest[0]):,.0f}/gr ({r_date}){emas_arrow}"

            if latest[1]:
                usd_arrow = arrow(float(latest[1]), float(prev[1]) if prev and prev[1] is not None else None)
                report += f"\n💵 *USD:* Rp {float(latest[1]):,.0f}{usd_arrow}"
            if latest[2]:
                gbp_arrow = arrow(float(latest[2]), float(prev[2]) if prev and prev[2] is not None else None)
                report += f"\n💷 *GBP:* Rp {float(latest[2]):,.0f}{gbp_arrow}"
    except Exception:
        pass

    # Compact family finance sections (merged from the Hermes cron report style)
    try:
        report += "\n\n" + _format_assets_section(db, scope_user_ids)
    except Exception:
        report += "\n\n💎 *Assets*\n• Gagal ambil data aset"

    try:
        report += "\n\n" + _format_debts_section(db, scope_user_ids, tz)
    except Exception:
        report += "\n\n🏦 *Debts/Hutang*\n• Gagal ambil data hutang"

    try:
        report += "\n\n" + _format_budget_compact_section(db, scope_user_ids, today)
    except Exception:
        report += "\n\n📊 *Budget*\n• Gagal ambil status budget"
    
    report += f"\n\n💡 *Insight:*\n{insight}"
    report += "\n\n🔍 Lihat detail di dashboard"
    
    return report

def _generate_daily_insight(stats: Dict, transaction_count: int) -> str:
    """Generate AI insight"""
    # Simply use fallback to keep it robust during rapid edits
    return _get_fallback_insight(stats.get("daily_balance",0), stats.get("expenses",0), stats.get("income",0), stats.get("category_breakdown",{}), stats.get("total_balance",0), transaction_count)

def _get_fallback_insight(daily_balance: float, expenses: float, income: float, category_breakdown: dict = None, total_balance: float = 0, transaction_count: int = 0) -> str:
    if expenses == 0: return "Belum ada pengeluaran hari ini. Keep it up! 💪"
    return f"Pengeluaran hari ini Rp {expenses:,.0f}. Jaga budget ya! 👍"

def generate_transaction_confirmation(db: Session, user_id: int, transaction_id: int = None, specific_category: str = None) -> dict:
    """Generate transaction confirmation data"""
    tz = ZoneInfo("Asia/Jakarta")
    today = datetime.now(tz).date()
    start_of_day_naive = datetime.combine(today, datetime.min.time())
    end_of_day_naive = datetime.combine(today, datetime.max.time())

    # Query today's totals using naive comparison + timezone conversion
    all_today = db.query(Transaction).filter(
        func.timezone('Asia/Jakarta', Transaction.created_at) >= start_of_day_naive,
        func.timezone('Asia/Jakarta', Transaction.created_at) <= end_of_day_naive,
        Transaction.is_deleted == False,
        Transaction.user_id == user_id
    ).all()

    if transaction_id:
        display_transactions = db.query(Transaction).filter(Transaction.id == transaction_id).all()
    else:
        display_transactions = sorted(all_today, key=lambda t: t.created_at, reverse=True)[:1]

    tx_list_lines = []
    for t in display_transactions:
        if t.category and "adjustment" in t.category.lower():
            continue
        time_str = t.created_at.astimezone(tz).strftime('%H:%M')
        amount_str = f"Rp {float(t.amount):,.0f}".replace(',', '.')
        tx_list_lines.append(f"- {time_str} | {amount_str} | {clean_description(t.raw_input or t.description or 'No desc')} | {t.category or 'Lain-lain'}")
    
    total_expense = float(sum(t.amount for t in all_today 
                              if t.type == TransactionType.EXPENSE 
                              and not (t.category and "adjustment" in t.category.lower())) or 0)
    
    # Simplified budget check
    sisa_budget_str = "Rp 0 (Budget not set)"
    try:
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        start_day = pref.start_of_month if pref else 1
        budget_month = today.month
        budget_year = today.year
        
        budget_records = db.query(Budget).filter(Budget.user_id == user_id, Budget.year == budget_year, Budget.month == budget_month).all()
        total_budget = float(sum(b.amount for b in budget_records) or 0)
        
        # Monthly spent
        month_start_naive = today.replace(day=start_day)
        if today.day < start_day:
            month_start_record = (today.replace(day=1) - timedelta(days=1)).replace(day=start_day)
            month_start_naive = month_start_record

        month_expense_total = db.query(func.sum(Transaction.amount)).filter(
            func.timezone('Asia/Jakarta', Transaction.created_at) >= month_start_naive,
            Transaction.is_deleted == False,
            Transaction.type == TransactionType.EXPENSE,
            ~Transaction.category.ilike('%adjustment%'),
            Transaction.user_id == user_id
        ).scalar() or 0
    except Exception:
        pass

    return {
        "transactions_list": "\n".join(tx_list_lines),
        "total_today": f"Rp {total_expense:,.0f}".replace(',', '.'),
        "sisa_budget": sisa_budget_str,
        "insight": "Keep tracking your spending!"
    }

def generate_budget_report(db: Session, user_id: int) -> str:
    return "Budget report pending rebuild."

def generate_weekly_report(db: Session, user_id: int) -> str:
    return "Weekly report pending rebuild."

def generate_financial_advice_report(db: Session, user_id: int) -> str:
    return "Advice report pending rebuild."

def generate_monthly_analysis_report(db: Session, user_id: int) -> str:
    return "Monthly analysis pending rebuild."
