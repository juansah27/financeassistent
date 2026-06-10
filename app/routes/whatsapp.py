"""
WhatsApp Webhook routes for receiving messages from WhatsApp bot
"""
import re as regex
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional
from app.db import session, crud, models, crud_extended
from app.db.models import RecurrenceType, TransactionType
from app.db.crud_bot_reply import get_default_template, format_template, get_template_by_name, format_recurring_template, format_confirmation_template
from app.ai import classifier
from app.services import ocr

# ── Pending account confirmations ───────────────────────────────────────────
# Store pending transactions waiting for account selection
# Key: user_id, Value: {recurring_id, amount, category, description, type, created_at}
_pending_account_confirmations: dict = {}
_CONFIRMATION_TTL_SECONDS = 300  # 5 minutes


def _format_rp(value) -> str:
    return f"Rp {float(value or 0):,.0f}".replace(",", ".")


def _format_due_date_id(value) -> str:
    """Format due dates as DD-MM-YYYY in WIB."""
    if not value:
        return "-"
    from zoneinfo import ZoneInfo
    return value.astimezone(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y")


def _format_date_long_id(value) -> str:
    """Format dates as '1 Juni 2026' in WIB."""
    if not value:
        return "-"
    from zoneinfo import ZoneInfo
    month_names = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember",
    }
    local = value.astimezone(ZoneInfo("Asia/Jakarta"))
    return f"{local.day} {month_names[local.month]} {local.year}"


def format_account_balance_snapshot(db: Session, user_id: int, account_ids: Optional[list[int]] = None) -> str:
    """Compact saldo snapshot for only the user/account touched by a transaction."""
    account_ids = [acc_id for acc_id in (account_ids or []) if acc_id]

    account_query = db.query(models.Account).filter(models.Account.is_active == True)
    if account_ids:
        account_query = account_query.filter(models.Account.id.in_(account_ids))
    else:
        account_query = account_query.filter(models.Account.user_id == user_id)

    accounts = account_query.order_by(models.Account.user_id, models.Account.type, models.Account.name).all()
    if not accounts:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return ""
        return f"💳 *Sisa Saldo*\n👤 *{user.username}* — akun tidak terdeteksi"

    user_ids = sorted({acc.user_id for acc in accounts})
    users = db.query(models.User).filter(models.User.id.in_(user_ids)).order_by(models.User.id).all()
    users_by_id = {u.id: u for u in users}

    accounts_by_user = {}
    for acc in accounts:
        accounts_by_user.setdefault(acc.user_id, []).append(acc)

    type_icons = {
        "CASH": "💰",
        "BANK": "🏦",
        "EWALLET": "📱",
        "INVESTMENT": "📈",
        "KREDIT": "💳",
    }
    
    lines = ["💳 *Sisa Saldo Terkait*"]
    touched_total = 0
    for i, uid in enumerate(user_ids):
        user = users_by_id.get(uid)
        user_accounts = accounts_by_user.get(uid, [])
        user_total = sum(float(acc.balance or 0) for acc in user_accounts)
        touched_total += user_total
        # Add blank line between users (not before first)
        if i > 0:
            lines.append("")
        lines.append(f"👤 *{user.username if user else uid}*")
        for acc in user_accounts:
            acc_type = acc.type.name if hasattr(acc.type, "name") else str(acc.type)
            icon = type_icons.get(acc_type, "💳")
            if acc_type == "KREDIT":
                # Show credit card usage: balance is negative (used), credit_limit is total
                used = abs(float(acc.balance or 0))
                limit = float(acc.credit_limit or 0)
                remaining = limit - used
                lines.append(f"   {icon} {acc.name}: {_format_rp(remaining)} tersisa dari {_format_rp(limit)}")
            else:
                lines.append(f"   {icon} {acc.name}: {_format_rp(acc.balance)}")

    if len(user_ids) > 1 or len(accounts) > 1:
        lines.append("")
        lines.append(f"💵 Total akun terkait: {_format_rp(touched_total)}")
    return "\n".join(lines)


def format_family_balance_snapshot(db: Session) -> str:
    """Full active account balance snapshot for explicit family balance commands."""
    accounts = db.query(models.Account).filter(
        models.Account.is_active == True
    ).order_by(models.Account.user_id, models.Account.type, models.Account.name).all()
    if not accounts:
        return "💳 *Saldo Keluarga*\n• Belum ada akun aktif"

    user_ids = sorted({acc.user_id for acc in accounts})
    users = db.query(models.User).filter(models.User.id.in_(user_ids)).order_by(models.User.id).all()
    users_by_id = {u.id: u for u in users}
    accounts_by_user = {}
    for acc in accounts:
        accounts_by_user.setdefault(acc.user_id, []).append(acc)

    type_icons = {
        "CASH": "💰",
        "BANK": "🏦",
        "EWALLET": "📱",
        "INVESTMENT": "📈",
        "KREDIT": "💳",
    }
    lines = ["💳 *Saldo Keluarga*"]
    grand_total = 0
    for i, uid in enumerate(user_ids):
        user_accounts = accounts_by_user.get(uid, [])
        user_total = sum(float(acc.balance or 0) for acc in user_accounts)
        grand_total += user_total
        user = users_by_id.get(uid)
        # Add blank line between users (not before first)
        if i > 0:
            lines.append("")
        lines.append(f"👤 *{user.username if user else uid}* — {_format_rp(user_total)}")
        for acc in user_accounts:
            acc_type = acc.type.name if hasattr(acc.type, "name") else str(acc.type)
            icon = type_icons.get(acc_type, "💳")
            if acc_type == "KREDIT":
                # Show credit card usage: balance is negative (used), credit_limit is total
                used = abs(float(acc.balance or 0))
                limit = float(acc.credit_limit or 0)
                remaining = limit - used
                lines.append(f"   {icon} {acc.name}: {_format_rp(remaining)} tersisa dari {_format_rp(limit)}")
            else:
                lines.append(f"   {icon} {acc.name}: {_format_rp(acc.balance)}")
    lines.append("")
    lines.append(f"💵 Total keluarga: {_format_rp(grand_total)}")
    return "\n".join(lines)


def format_recurring_list_snapshot(recurring_list, title: str = "Daftar Tagihan") -> str:
   """Human-friendly recurring list for WhatsApp commands."""
   if not recurring_list:
       return f"🔄 *{title}*\n\n• Belum ada tagihan yang cocok"

   active_items = [item for item in recurring_list if item.is_active]
   inactive_count = len(recurring_list) - len(active_items)
   visible_items = active_items or recurring_list
   visible_items = sorted(visible_items, key=lambda item: (item.next_due_date is None, item.next_due_date))
   status_label = "belum dibayar" if active_items else "semua data"

   paylater_keywords = ('paylater', 'gopaylater', 'kredivo', 'cicilan', 'kredit', 'hutang')

   def item_type_name(item) -> str:
       value = getattr(item, "type", None)
       return value.name if hasattr(value, "name") else str(value or "")

   def is_paylater_item(item) -> bool:
       haystack = f"{item.description or ''} {item.category or ''}".lower()
       return any(keyword in haystack for keyword in paylater_keywords)

   if title == "Daftar Paylater":
       sections = [("💳 Paylater / Cicilan", visible_items)]
       income_items = []
       outgoing_items = visible_items
       other_items = []
   else:
       paylater_items = [item for item in visible_items if is_paylater_item(item)]
       income_items = [item for item in visible_items if item_type_name(item) == "INCOME" and not is_paylater_item(item)]
       bill_items = [
           item for item in visible_items
           if item_type_name(item) in ("EXPENSE", "DEBT", "SAVING", "INVESTMENT")
           and not is_paylater_item(item)
       ]
       other_items = [
           item for item in visible_items
           if item not in paylater_items and item not in income_items and item not in bill_items
       ]
       outgoing_items = paylater_items + bill_items + [item for item in other_items if item_type_name(item) != "INCOME"]
       sections = [
           ("💳 Paylater / Cicilan", paylater_items),
           ("📌 Tagihan Keluar", bill_items),
           ("💰 Pemasukan Masuk", income_items),
           ("📎 Lainnya", other_items),
       ]

   visible_count = len(visible_items)
   total_income = sum(float(item.amount or 0) for item in income_items)
   total_outgoing = sum(float(item.amount or 0) for item in outgoing_items)
   net_amount = total_income - total_outgoing

   lines = [
       f"🔄 *{title}*",
       f"• Status: {status_label}",
       f"• Total item: {visible_count}",
       f"• Pemasukan: {_format_rp(total_income)}",
       f"• Pengeluaran/tagihan: {_format_rp(total_outgoing)}",
   ]
   if total_income:
       lines.append(f"• Selisih: {_format_rp(net_amount)}")
   lines.append("")

   shown_count = 0
   max_items = 20
   for section_title, section_items in sections:
       if not section_items or shown_count >= max_items:
           continue
       section_total = sum(float(item.amount or 0) for item in section_items)
       lines.append(f"*{section_title}* — {_format_rp(section_total)}")

       current_due = None
       for item in section_items:
           if shown_count >= max_items:
               break
           due = _format_date_long_id(item.next_due_date)
           if due != current_due:
               current_due = due
               lines.append(f"📅 *{due}*")

           remaining = getattr(item, "remaining_occurrences", None)
           if remaining == 1:
               remaining_text = "sekali bayar"
           elif remaining:
               remaining_text = f"sisa {remaining} kali"
           elif not item.is_active:
               remaining_text = "nonaktif"
           else:
               remaining_text = ""
           remaining_suffix = f" — {remaining_text}" if remaining_text else ""
           lines.append(f"• {item.description}: {_format_rp(item.amount)}{remaining_suffix}")
           shown_count += 1
       lines.append("")

   if len(visible_items) > shown_count:
       lines.append(f"• +{len(visible_items) - shown_count} item lain belum ditampilkan")
   if active_items and inactive_count:
       lines.append(f"• {inactive_count} tagihan lama/nonaktif disembunyikan")
   return "\n".join(lines)


def _infer_due_year(day: int, month: int, reference_dt=None, overdue_grace_days: int = 45) -> int:
    """Infer year for month/day due dates that omit a year.

    Rule:
    - future/today in current year => current year
    - recent past (<= overdue_grace_days) => current year, treated as overdue
    - far past (> overdue_grace_days) => next year
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    wib = ZoneInfo("Asia/Jakarta")
    if reference_dt is None:
        reference_dt = datetime.now(wib)
    elif reference_dt.tzinfo is None:
        reference_dt = reference_dt.replace(tzinfo=wib)
    else:
        reference_dt = reference_dt.astimezone(wib)

    today = reference_dt.date()
    candidate = datetime(today.year, month, day, tzinfo=wib).date()
    if candidate >= today:
        return today.year

    days_overdue = (today - candidate).days
    if days_overdue <= overdue_grace_days:
        return today.year
    return today.year + 1


def _extract_fixed_due_date(text: str, reference_dt=None):
    """Extract a natural-language due date from text.

    Supports:
    - 27 juni 2026
    - 27 juni (year inferred safely)
    - #due 27 juni 2026
    - 2026-06-27
    - #on 2026-06-27
    - jatuh tempo 1 juli 2026
    - jatuh tempo 1 juli (year inferred safely)
    - tempo 1 juli 2026

    Returns (aware_utc_datetime, matched_span) or (None, None).
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    month_map = {
        "januari": 1, "jan": 1,
        "februari": 2, "feb": 2,
        "maret": 3, "mar": 3,
        "april": 4, "apr": 4,
        "mei": 5,
        "juni": 6, "jun": 6,
        "juli": 7, "jul": 7,
        "agustus": 8, "agu": 8, "aug": 8,
        "september": 9, "sep": 9,
        "oktober": 10, "okt": 10,
        "november": 11, "nov": 11,
        "desember": 12, "des": 12,
    }
    month_names = "januari|jan|februari|feb|maret|mar|april|apr|mei|juni|jun|juli|jul|agustus|agu|aug|september|sep|oktober|okt|november|nov|desember|des"

    patterns = [
        ("dmy_year", rf'(?:(?:#due|#on|due|pada|tgl|tanggal|jatuh\s+tempo|tempo)\s*)?(\d{{1,2}})\s+({month_names})\s+(\d{{4}})'),
        ("iso", r'(?:(?:#due|#on|due|pada|tgl|tanggal|jatuh\s+tempo|tempo)\s*)?(\d{4})-(\d{2})-(\d{2})'),
        ("dmy_no_year", rf'(?:(?:#due|#on|due|pada|tgl|tanggal|jatuh\s+tempo|tempo)\s*)?(\d{{1,2}})\s+({month_names})(?!\s+\d{{4}})'),
    ]

    matches = []
    for kind, pattern in patterns:
        for match in regex.finditer(pattern, text, flags=regex.IGNORECASE):
            matches.append((match.start(), match.end(), kind, match))

    if not matches:
        return None, None

    _, _, kind, m = sorted(matches, key=lambda item: (item[0], item[1]))[-1]
    groups = m.groups()

    if kind == "iso":
        year = int(groups[0])
        month = int(groups[1])
        day = int(groups[2])
    else:
        day = int(groups[0])
        month = month_map[groups[1].lower()]
        if kind == "dmy_year":
            year = int(groups[2])
        else:
            year = _infer_due_year(day, month, reference_dt=reference_dt)

    wib = ZoneInfo("Asia/Jakarta")
    try:
        local_dt = datetime(year, month, day, 0, 0, 0, tzinfo=wib)
    except ValueError:
        return None, None
    return local_dt.astimezone(timezone.utc), m.span()


def _looks_like_recurring_natural(text: str) -> bool:
    lower = text.lower()
    recurring_keywords = [
        'jatuh tempo', 'tempo', 'due', 'tagihan', 'cicilan', 'angsuran',
        'paylater', 'gopaylater', 'kredivo', 'akulaku', 'shopeepaylater',
        'spaylater', 'pinjaman', 'hutang', 'kredit', 'berlangganan', 'subscription'
    ]
    return any(keyword in lower for keyword in recurring_keywords)


def _build_recurring_description(text: str) -> str:
    cleaned = _strip_whatsapp_export_prefix(text)
    cleaned = regex.sub(r'(?i)\b(?:jatuh\s+tempo|tempo|due|pada|tgl|tanggal|#due|#on|#recurring|#monthly|#yearly|#custom)\b', ' ', cleaned)
    cleaned = regex.sub(r'(?i)\b(?:paylater|gopaylater|kredivo|akulaku|shopeepaylater|spaylater)\b', lambda m: m.group(0), cleaned)
    cleaned = regex.sub(r'(?i)\b(?:\d{1,2}\s+(?:januari|jan|februari|feb|maret|mar|april|apr|mei|juni|jun|juli|jul|agustus|agu|aug|september|sep|oktober|okt|november|nov|desember|des)\s+\d{4}|\d{4}-\d{2}-\d{2})\b', ' ', cleaned)
    cleaned = regex.sub(r'(?<!\d)(?:rp\s*)?\d+(?:[.,]\d{3})*(?:\s*(?:rb|ribu|k|jt|juta))?(?!\d)', ' ', cleaned, flags=regex.IGNORECASE)
    cleaned = regex.sub(r'\s+', ' ', cleaned).strip(' -_\t')
    return cleaned or text.strip()


def _strip_whatsapp_export_prefix(text: str) -> str:
    """Strip copied WhatsApp export prefix like '[5/28, 01:19] Ndoro ❤️: ...'."""
    return regex.sub(r'^\s*\[[^\]]+\]\s*[^:]{1,80}:\s*', '', text).strip()


def _extract_recurring_amount(text: str, due_span=None):
    """Extract the recurring nominal, preferring the last amount before the due-date phrase.

    This avoids reading date parts / years (01, 2026) as the amount.
    Supports: 73077, 73.077, 97,170, 97rb, 97.5k, 1jt.
    """
    work_text = _strip_whatsapp_export_prefix(text)
    if due_span:
        work_text = work_text[:due_span[0]]
    work_text = regex.split(r'(?i)\b(?:jatuh\s+tempo|tempo|due|pada|tgl|tanggal|#due|#on)\b', work_text)[0]

    amount_pattern = regex.compile(
        r'(?<!\d)(?:rp\s*)?(\d+(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta))?(?!\d)',
        flags=regex.IGNORECASE,
    )
    matches = list(amount_pattern.finditer(work_text))
    if not matches:
        return None

    match = matches[-1]
    raw_number = match.group(1)
    suffix = (match.group(2) or '').lower()

    if suffix in {'rb', 'ribu', 'k'}:
        numeric = float(raw_number.replace(',', '.')) * 1000
    elif suffix in {'jt', 'juta'}:
        numeric = float(raw_number.replace(',', '.')) * 1000000
    else:
        # Treat dot/comma as thousand separators when followed by exactly 3 digits.
        if regex.search(r'[.,]\d{3}$', raw_number):
            numeric = float(raw_number.replace('.', '').replace(',', ''))
        else:
            numeric = float(raw_number.replace(',', '.'))
    return numeric


def _extract_money_amount(text: str):
    amount_pattern = regex.compile(
        r'(?<!\d)(?:rp\s*)?(\d+(?:[.,]\d{3})*|\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta))?(?!\d)',
        flags=regex.IGNORECASE,
    )
    matches = list(amount_pattern.finditer(text))
    if not matches:
        return None
    match = matches[-1]
    raw_number = match.group(1)
    suffix = (match.group(2) or '').lower()
    if suffix in {'rb', 'ribu', 'k'}:
        return float(raw_number.replace(',', '.')) * 1000
    if suffix in {'jt', 'juta'}:
        return float(raw_number.replace(',', '.')) * 1000000
    if regex.search(r'[.,]\d{3}$', raw_number):
        return float(raw_number.replace('.', '').replace(',', ''))
    return float(raw_number.replace(',', '.'))


def _clean_party_name(value: str) -> str:
    cleaned = (value or '').strip().strip('.,;:-_')
    cleaned = regex.sub(r'(?i)\s+(?:dari|ke)\s+(?:dompet|cash|atm\s+bca|atm\s+bri|bca|bri|gopay|shopeepay|spay|visa|jago).*$','', cleaned).strip()
    cleaned = regex.sub(r'\s+', ' ', cleaned)
    return cleaned.strip().strip('.,;:-_')


def _party_display(value: str) -> str:
    value = _clean_party_name(value)
    known = {
        'ayah': 'Ayah', 'papa': 'Ayah', 'juansah': 'Ayah',
        'bunda': 'Bunda', 'mama': 'Bunda', 'sella': 'Bunda',
        'gavin': 'Gavin', 'anak': 'Gavin', 'dedek': 'Gavin',
    }
    return known.get(value.lower(), ' '.join(part.capitalize() for part in value.split()))


def _resolve_family_user(db: Session, name: str):
    name_lower = _clean_party_name(name).lower()
    aliases = {
        'ayah': ['ayah', 'papa', 'juansah'],
        'bunda': ['bunda', 'mama', 'sella'],
        'gavin': ['gavin', 'anak', 'dedek'],
    }
    users = db.query(models.User).order_by(models.User.id).all()
    for user in users:
        username_lower = (user.username or '').lower()
        candidates = {username_lower, *aliases.get(username_lower, [])}
        if name_lower in candidates:
            return user
    return None


def _default_dompet_account_id(db: Session, user_id: int):
    accounts = db.query(models.Account).filter(
        models.Account.user_id == user_id,
        models.Account.is_active == True,
    ).order_by(models.Account.id).all()
    if not accounts:
        return None
    for account in accounts:
        if 'dompet' in (account.name or '').lower() or 'cash' in (account.name or '').lower():
            return account.id
    return accounts[0].id


def _detect_or_default_account_id(text: str, user_id: int, db: Session):
    return detect_account_from_text(text, user_id, db) or _default_dompet_account_id(db, user_id)


def _debt_like_filter(counterparty: str):
    pattern = f"%{counterparty}%"
    return (
        models.Debt.creditor.ilike(pattern)
        | models.Debt.name.ilike(pattern)
        | models.Debt.notes.ilike(pattern)
    )


def _find_payable_debt(db: Session, payer_id: int, counterparty: str):
    return db.query(models.Debt).filter(
        models.Debt.is_active == True,
        ((models.Debt.debtor_user_id == payer_id) | (models.Debt.user_id == payer_id)),
        _debt_like_filter(counterparty),
    ).order_by(models.Debt.created_at.desc(), models.Debt.id.desc()).first()


def _find_receivable_debt(db: Session, receiver_id: int, counterparty: str):
    return db.query(models.Debt).filter(
        models.Debt.is_active == True,
        ((models.Debt.creditor_user_id == receiver_id) | (models.Debt.user_id == receiver_id)),
        _debt_like_filter(counterparty),
    ).order_by(models.Debt.created_at.desc(), models.Debt.id.desc()).first()


def _apply_debt_settlement(db: Session, debt: models.Debt, amount: float, transaction_id: int, notes: str = None):
    amount_dec = Decimal(str(amount))
    remaining = Decimal(str(debt.remaining_amount or 0))
    if amount_dec <= 0:
        return False, "Jumlah pembayaran harus lebih dari 0"
    if amount_dec > remaining:
        return False, f"Jumlah bayar ({_format_rp(amount_dec)}) melebihi sisa hutang ({_format_rp(remaining)})"

    payment = models.DebtPayment(
        debt_id=debt.id,
        transaction_id=transaction_id,
        amount=amount_dec,
        notes=notes,
    )
    debt.remaining_amount = remaining - amount_dec
    if debt.remaining_amount <= 0:
        debt.remaining_amount = Decimal('0')
        debt.is_active = False
    db.add(payment)
    db.commit()
    db.refresh(debt)
    return True, None


def _format_debt_reply(title: str, counterparty: str, amount: float, remaining=None, account_snapshot: str = None) -> str:
    lines = [title, "", f"• Pihak: {_party_display(counterparty)}", f"• Nominal: {_format_rp(amount)}"]
    if remaining is not None:
        remaining_dec = Decimal(str(remaining or 0))
        status = "lunas" if remaining_dec <= 0 else f"sisa {_format_rp(remaining_dec)}"
        lines.append(f"• Status: {status}")
    if account_snapshot:
        lines.extend(["", account_snapshot])
    return "\n".join(lines)


def _parse_debt_intent(message_text: str, default_user, db: Session):
    lower = message_text.lower().strip()
    amount = _extract_money_amount(message_text)
    if amount is None:
        return None

    amount_pattern = r'(?:rp\s*)?\d+(?:[.,]\d{3})*|(?:rp\s*)?\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta))?'
    # Prefer receive-payment wording before generic bayar patterns.
    receive_patterns = [
        rf'^(?:(?P<receiver>[a-zA-Z0-9_\s]+?)\s+)?(?:terima|nerima|menerima)\s+(?:pembayaran\s+)?hutang\s+(?P<amount>{amount_pattern})\s+dari\s+(?P<counterparty>.+)$',
        rf'^(?P<counterparty>.+?)\s+(?:bayar|cicil|nyicil|lunasin)\s+(?:hutang\s+)?(?P<amount>{amount_pattern})\s+ke\s+(?P<receiver>ayah|papa|juansah|bunda|mama|sella|gavin|anak|dedek)\b.*$',
    ]
    for pattern in receive_patterns:
        match = regex.search(pattern, message_text, flags=regex.IGNORECASE)
        if not match:
            continue
        receiver_name = match.groupdict().get('receiver') or (default_user.username if default_user else '')
        receiver = _resolve_family_user(db, receiver_name) or default_user
        counterparty = _clean_party_name(match.groupdict().get('counterparty'))
        if receiver and counterparty:
            matched_amount = _extract_money_amount(match.groupdict().get('amount') or '') or amount
            return {"intent": "receive_payment", "receiver": receiver, "counterparty": counterparty, "amount": matched_amount}

    pay_patterns = [
        rf'^(?:(?P<payer>[a-zA-Z0-9_\s]+?)\s+)?(?:bayar|cicil|nyicil|lunasin)\s+(?:hutang\s+)?(?P<amount>{amount_pattern})\s+ke\s+(?P<counterparty>.+)$',
        rf'^(?:(?P<payer>[a-zA-Z0-9_\s]+?)\s+)?(?:bayar|cicil|nyicil|lunasin)\s+ke\s+(?P<counterparty>.+?)\s+(?P<amount>{amount_pattern}).*$',
    ]
    for pattern in pay_patterns:
        match = regex.search(pattern, message_text, flags=regex.IGNORECASE)
        if not match:
            continue
        payer_name = match.groupdict().get('payer') or (default_user.username if default_user else '')
        payer = _resolve_family_user(db, payer_name) or default_user
        counterparty = _clean_party_name(match.groupdict().get('counterparty'))
        if payer and counterparty:
            matched_amount = _extract_money_amount(match.groupdict().get('amount') or '') or amount
            return {"intent": "pay_debt", "payer": payer, "counterparty": counterparty, "amount": matched_amount}

    create_patterns = [
        rf'^(?P<subject>[a-zA-Z0-9_\s]+?)\s+(?:hutang|pinjem|minjem)\s+(?P<amount>{amount_pattern})\s+(?:ke|dari)\s+(?P<target>.+)$',
        rf'^(?:hutang|pinjem|minjem)\s+(?P<amount>{amount_pattern})\s+(?:ke|dari)\s+(?P<target>.+)$',
    ]
    for pattern in create_patterns:
        match = regex.search(pattern, message_text, flags=regex.IGNORECASE)
        if not match:
            continue
        subject_name = match.groupdict().get('subject') or (default_user.username if default_user else '')
        target_name = _clean_party_name(match.groupdict().get('target'))
        subject_user = _resolve_family_user(db, subject_name)
        target_user = _resolve_family_user(db, target_name)
        matched_amount = _extract_money_amount(match.groupdict().get('amount') or '') or amount
        if subject_user:
            return {
                "intent": "create_debt",
                "debtor": subject_user,
                "creditor_user": target_user,
                "counterparty": target_user.username if target_user else target_name,
                "amount": matched_amount,
            }
        if target_user:
            return {
                "intent": "create_receivable",
                "creditor_user": target_user,
                "counterparty": _clean_party_name(subject_name),
                "amount": matched_amount,
            }
    return None


# Account detection: map keywords to account IDs based on sender
def detect_account_from_text(text: str, user_id: int, db: Session):
    text_lower = text.lower()
    
    # Get user's active accounts from DB (deterministic order)
    accounts = db.query(models.Account).filter(
        models.Account.user_id == user_id,
        models.Account.is_active == True
    ).order_by(models.Account.id).all()
    
    # Build global keyword list: (acc_id, keyword) pairs, sorted by length desc
    all_keywords = []
    for acc in accounts:
        name_lower = acc.name.lower()
        keywords = [name_lower]
        if 'bca' in name_lower:
            keywords.append('bca')
        if 'bri' in name_lower:
            keywords.append('bri')
        if 'gopay' in name_lower:
            keywords.append('gopay')
        if 'shopeepay' in name_lower:
            keywords.append('shopeepay')
        if 'dompet' in name_lower or 'cash' in name_lower:
            keywords.append('cash')
            keywords.append('dompet')
        if 'atm' in name_lower:
            keywords.append('atm')
        if 'visa' in name_lower:
            keywords.append('visa')
        if 'jago' in name_lower:
            keywords.append('jago')
        # Also add individual words from the account name as keywords (>= 3 chars)
        for word in name_lower.split():
            if len(word) >= 3 and word not in keywords:
                keywords.append(word)
        for kw in keywords:
            all_keywords.append((len(kw), acc.id, kw))
    
    # Sort global: longest keyword first (across ALL accounts)
    all_keywords.sort(key=lambda x: x[0], reverse=True)
    
    for _, acc_id, kw in all_keywords:
        if kw in text_lower:
            return acc_id
    
    # Default: Dompet for expenses, ATM BCA for income
    for acc in accounts:
        if 'dompet' in acc.name.lower():
            return acc.id
    
    return None  # No match, account_id stays NULL

def detect_accounts_from_text(text: str, user_id: int, db: Session):
    """Detect source & destination accounts + destination user for transfer commands.
    Returns (source_account_id, destination_account_id, destination_user_id)
    - source_account_id: None if not detected
    - destination_account_id: None if not detected
    - destination_user_id: user_id of the recipient (defaults to same user)
    """
    text_lower = text.lower()
    
    # Get current user's active accounts (deterministic order)
    user_accounts = db.query(models.Account).filter(
        models.Account.user_id == user_id,
        models.Account.is_active == True
    ).order_by(models.Account.id).all()
    
    def get_account_kw(acc):
        """Build keyword list for an account"""
        name_lower = acc.name.lower()
        kw = [name_lower]
        if 'bca' in name_lower: kw.append('bca')
        if 'bri' in name_lower: kw.append('bri')
        if 'gopay' in name_lower: kw.append('gopay')
        if 'shopeepay' in name_lower: kw.append('shopeepay')
        if 'dompet' in name_lower or 'cash' in name_lower: kw.extend(['cash', 'dompet'])
        if 'atm' in name_lower: kw.append('atm')
        if 'visa' in name_lower: kw.append('visa')
        if 'jago' in name_lower: kw.append('jago')
        # Also add individual words from the account name as keywords (>= 3 chars)
        for word in name_lower.split():
            if len(word) >= 3 and word not in kw:
                kw.append(word)
        return sorted(kw, key=len, reverse=True)
    
    # Build keyword map: account_id -> keywords
    acc_kw_map = {}
    for acc in user_accounts:
        acc_kw_map[acc.id] = get_account_kw(acc)
    
    # Get family user name mappings
    user_names = {}
    current_user = db.query(models.User).filter(models.User.id == user_id).first()
    if current_user and current_user.family_id:
        family_users = db.query(models.User).filter(models.User.family_id == current_user.family_id).all()
        for u in family_users:
            user_names[u.username.lower()] = u.id
    
    # Detect destination user
    dest_user_id = user_id
    possible_names = [n for n in user_names.keys() if n != current_user.username.lower()]
    for name, uid in user_names.items():
        if uid != user_id and name in text_lower:
            dest_user_id = uid
            break
    
    # Get destination user's accounts if different user
    dest_accounts = db.query(models.Account).filter(
        models.Account.user_id == dest_user_id,
        models.Account.is_active == True
    ).all() if dest_user_id != user_id else user_accounts
    
    dest_kw_map = {}
    for acc in dest_accounts:
        if acc.user_id == dest_user_id:
            dest_kw_map[acc.id] = get_account_kw(acc)
    
    def find_best_match(kw_map, exclude_ids=None):
        """Find best matching account from keyword map"""
        if exclude_ids is None:
            exclude_ids = set()
        for acc_id, kws in kw_map.items():
            if acc_id in exclude_ids:
                continue
            for kw in kws:
                if kw in text_lower:
                    return acc_id
        return None
    
    # Strategy: parse "dari X ke Y" patterns
    # Check for source indicators
    src_keywords = ["dari", "dari akun"]
    dest_keywords = ["ke ", "buat ", "untuk ", "masuk ke "]
    
    source_acc_id = None
    dest_acc_id = None
    
    # First pass: look for "dari X ke Y" or "X ke Y" pattern
    # Try to find words after "dari" for source
    dari_match = regex.search(r'dari\s+([\w\s]+?)(?:\s+ke\b|\s+buat\b|\s+untuk\b|\s+masuk\b|$)', text_lower)
    ke_match = regex.search(r'\bke\s+([\w\s]+?)(?:\s+dari\b|\s+buat\b|\s+untuk\b|\s+masuk\b|$)', text_lower)
    
    source_hint = dari_match.group(1) if dari_match else None
    dest_hint = ke_match.group(1) if ke_match else None
    
    # Try matching source hint
    if source_hint:
        for acc_id, kws in acc_kw_map.items():
            if source_hint in kws or any(kw.startswith(source_hint) for kw in kws):
                source_acc_id = acc_id
                break
    
    # Try matching dest hint (strip username from hint if present)
    if dest_hint:
        # Strip leading/trailing whitespace
        dest_hint_clean = dest_hint.strip()
        for acc_id, kws in dest_kw_map.items():
            # Check exact match, or kw is in hint, or hint starts with kw, or kw starts with hint
            if (dest_hint_clean in kws or 
                any(kw == dest_hint_clean for kw in kws) or
                any(dest_hint_clean.startswith(kw) for kw in kws) or
                any(kw.startswith(dest_hint_clean) for kw in kws)):
                dest_acc_id = acc_id
                break
    
    # Fallback: if source not found, find any account mentioned (not dest)
    if not source_acc_id:
        for acc_id, kws in acc_kw_map.items():
            if acc_id == dest_acc_id:
                continue
            for kw in kws:
                if kw in text_lower:
                    source_acc_id = acc_id
                    break
            if source_acc_id:
                break
    
    # If still no source, try "ambil/tarik" pattern - source is the ATM/bank mentioned
    if not source_acc_id:
        for word in ["ambil", "tarik", "withdraw"]:
            if word in text_lower:
                # Build global keyword list for ATM accounts (longest first)
                atm_candidates = []
                for acc_id, kws in acc_kw_map.items():
                    for kw in kws:
                        if kw in ['bca', 'bri', 'atm']:
                            atm_candidates.append((len(kw), acc_id, kw))
                atm_candidates.sort(key=lambda x: x[0], reverse=True)
                
                for _, acc_id, kw in atm_candidates:
                    if kw in text_lower:
                        source_acc_id = acc_id
                        break
                if source_acc_id:
                    break
    
    # Cross-user fallback: if no dest found, search ALL family members' accounts
    if not dest_acc_id and dest_hint:
        all_family_accounts = db.query(models.Account).filter(
            models.Account.is_active == True
        ).all()
        dest_hint_clean = dest_hint.strip()
        for acc in all_family_accounts:
            acc_kws = get_account_kw(acc)
            if (dest_hint_clean in acc_kws or
                any(kw == dest_hint_clean for kw in acc_kws) or
                any(dest_hint_clean.startswith(kw) for kw in acc_kws) or
                any(kw.startswith(dest_hint_clean) for kw in acc_kws)):
                if acc.id != source_acc_id:
                    dest_acc_id = acc.id
                    dest_user_id = acc.user_id
                    break

    # If still no dest, default dest to Dompet (current user)
    if not dest_acc_id:
        for acc_id, kws in dest_kw_map.items():
            if 'dompet' in ' '.join(kws) or 'cash' in ' '.join(kws):
                if acc_id != source_acc_id:
                    dest_acc_id = acc_id
                    break
    
    # If still no source, default source to Dompet
    if not source_acc_id:
        for acc_id, kws in acc_kw_map.items():
            if 'dompet' in ' '.join(kws) or 'cash' in ' '.join(kws):
                if acc_id != dest_acc_id:
                    source_acc_id = acc_id
                    break
    
    return source_acc_id, dest_acc_id, dest_user_id
from app.services.report_generator import (
    generate_daily_report, 
    generate_budget_report, 
    generate_weekly_report, 
    generate_financial_advice_report,
    generate_monthly_analysis_report
)
from app.services.financial_qna import FinancialQnAService
from app.services import smart_recurring
from datetime import timedelta, datetime, timezone
import os
import tempfile
import json
from pathlib import Path

router = APIRouter()

# Webhook secret for security
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    raise RuntimeError("WEBHOOK_SECRET environment variable is not set!")

class WhatsAppMessage(BaseModel):
    message: str
    sender: str
    sender_number: str
    group_name: str
    group_id: str
    timestamp: str
    message_id: str

def get_user_by_whatsapp(db: Session, sender_num: str) -> Optional[models.User]:
    """
    Resolve user based on sender_number or LID.
    """
    if not sender_num:
        return db.query(models.User).filter(models.User.id == 1).first() or db.query(models.User).first()
        
    # Strip suffixes (@s.whatsapp.net, @g.us, @lid, etc.)
    clean_sender = sender_num.split('@')[0]
    
    # Map known IDs to user IDs
    # Includes phone numbers (normalized) and LIDs
    wa_map = {
        "62895330533454": 1,   # Juansah (Phone)
        "62895330565959": 2,   # Sella (Phone)
        "186895535497441": 1,  # Juansah (LID)
        "256461271760979": 2,  # Sella (LID)
    }
    
    # Try direct match
    user_id = wa_map.get(clean_sender)
    
    # Try normalized phone match (remove +, -, spaces)
    if not user_id:
        normalized = regex.sub(r'\D', '', clean_sender)
        user_id = wa_map.get(normalized)
        
    if user_id:
        return db.query(models.User).filter(models.User.id == user_id).first()
    
    # Fallback: search by username if clean_sender looks like a name (rare)
    # Default fallback: return first user but log warning
    default_user = db.query(models.User).filter(models.User.id == 1).first() or db.query(models.User).first()
    print(f"⚠️ Unknown sender '{sender_num}' (cleaned: '{clean_sender}'), defaulting to user_id={default_user.id if default_user else 'N/A'}")
    return default_user

@router.get("/api/whatsapp/recurring-list")
async def get_whatsapp_recurring_list(
    search: Optional[str] = None,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: Session = Depends(session.get_db)
):
    """Return recurring transactions for WhatsApp bot commands."""
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    recurring_list = crud_extended.get_recurring_transactions(
        db,
        user_id=None,
        active_only=False,
        search_term=search
    )

    if search:
        q = search.lower().strip()
        if q == 'paylater':
            keywords = ['paylater', 'gopaylater', 'tagihan', 'cicilan', 'hutang', 'kredit']
            recurring_list = [
                item for item in recurring_list
                if any(kw in (item.description or '').lower() for kw in keywords)
                or any(kw in (item.category or '').lower() for kw in keywords)
            ]

    title = "Daftar Paylater" if search and search.lower().strip() == 'paylater' else "Daftar Tagihan"

    return JSONResponse({
        "success": True,
        "count": len(recurring_list),
        "recurring": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "description": item.description,
                "amount": float(item.amount or 0),
                "category": item.category,
                "next_due_date": item.next_due_date.isoformat() if item.next_due_date else None,
                "is_active": item.is_active,
                "recurrence_type": item.recurrence_type.value if getattr(item, "recurrence_type", None) else None,
            }
            for item in recurring_list
        ],
        "reply_message": format_recurring_list_snapshot(recurring_list, title=title)
    })


@router.post("/api/whatsapp/webhook")
async def whatsapp_webhook(
    message_data: WhatsAppMessage,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: Session = Depends(session.get_db)
):
    """
    Webhook endpoint to receive messages from WhatsApp bot
    """
    # Verify webhook secret
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        # Update or create WhatsApp Group info
        if message_data.group_id and "g.us" in message_data.group_id and message_data.group_name and message_data.group_name != "Unknown Group":
            try:
                existing_group = db.query(models.WhatsAppGroup).filter(
                    models.WhatsAppGroup.group_id == message_data.group_id
                ).first()
                
                if existing_group:
                    existing_group.name = message_data.group_name
                    existing_group.last_active_at = func.now()
                else:
                    new_group = models.WhatsAppGroup(
                        group_id=message_data.group_id,
                        name=message_data.group_name,
                        is_allowed=True 
                    )
                    db.add(new_group)
                
                db.commit()
            except Exception as e:
                print(f"Failed to update group info: {e}")
                db.rollback()

        message_text = message_data.message.strip()
        
        # Skip if message is too short
        # Skip if message is too short, UNLESS it's a confirmation reply
        lower_msg_check = message_text.lower()
        if len(message_text) < 3 and lower_msg_check not in ["ya", "y", "ok", "no", "n"]:
            return JSONResponse({
                "success": False,
                "reason": "Message too short"
            })
        
        # Resolve user based on sender_number
        default_user = get_user_by_whatsapp(db, message_data.sender_number or message_data.sender)
        
        # Check for pending account confirmation
        user_id = default_user.id if default_user else None
        if user_id and user_id in _pending_account_confirmations:
            pending = _pending_account_confirmations[user_id]
            # Check TTL (5 minutes)
            pending_time = pending.get("created_at")
            if pending_time:
                elapsed = (datetime.now(timezone.utc) - pending_time).total_seconds()
                if elapsed > _CONFIRMATION_TTL_SECONDS:
                    # Expired, remove pending
                    del _pending_account_confirmations[user_id]
                else:
                    # Try to detect account from user's reply
                    account_id = detect_account_from_text(message_text, user_id, db)
                    if account_id:
                        # Create the pending transaction
                        tx = crud.create_transaction(
                            db=db,
                            user_id=user_id,
                            transaction_type=pending["type"],
                            amount=pending["amount"],
                            category=pending["category"],
                            description=pending["description"],
                            raw_input=pending.get("raw_input", ""),
                            account_id=account_id,
                            recurring_id=pending.get("recurring_id")
                        )
                        # Update recurring if linked
                        if pending.get("recurring_id"):
                            from app.db import crud_extended as crud_ext
                            recurring = db.query(models.RecurringTransaction).filter(
                                models.RecurringTransaction.id == pending["recurring_id"]
                            ).first()
                            if recurring:
                                _update_recurring_after_payment(db, recurring, tx.created_at)
                        
                        # Remove pending
                        del _pending_account_confirmations[user_id]
                        
                        # Return success
                        amount_str = f"Rp {tx.amount:,.0f}".replace(",", ".")
                        reply_msg = (
                            "✅ *Transaksi tercatat*\n\n"
                            f"• Nominal: {amount_str}\n"
                            f"• Kategori: {tx.category}\n"
                            f"• Deskripsi: {tx.description}"
                        )
                        # Add balance info
                        balance_account_ids = [account_id]
                        reply_msg = reply_msg + "\n\n" + format_account_balance_snapshot(
                            db, user_id, account_ids=balance_account_ids
                        )
                        return JSONResponse({
                            "success": True,
                            "message": "Transaction created with selected account",
                            "transaction_id": tx.id,
                            "reply_message": reply_msg
                        })
                    else:
                        # Still can't detect account, ask again
                        accounts = db.query(models.Account).filter(
                            models.Account.user_id == user_id,
                            models.Account.is_active == True
                        ).all()
                        account_list = "\n".join([f"• {acc.name}" for acc in accounts])
                        reply_msg = (
                            f"❓ *Akun tidak dikenali*\n\n"
                            f"Untuk tagihan *{pending['description']}* (Rp {pending['amount']:,.0f}):\n\n"
                            f"Pilih akun yang tersedia:\n{account_list}\n\n"
                            f"Ketik nama akun yang ingin digunakan."
                        )
                        return JSONResponse({
                            "success": True,
                            "message": "Account not recognized, asking again",
                            "reply_message": reply_msg
                        })
        
        # Check for specific commands (Non-transactional)
        # Ensure we strip whitespace for accurate matching
        lower_msg = message_text.lower().strip()
        
        if lower_msg in ["!help", "help", "bantuan", "menu", "perintah", "command"]:
            report_msg = (
                "🤖 *Menu Bantuan Bot Keuangan*\n\n"
                "Ketik perintah atau catatan keuangan langsung di grup. Contoh yang bisa dipakai:\n\n"
                "📝 *Catat transaksi*\n"
                '• "beli nasi goreng 15k"\n'
                '• "gajian 5jt"\n'
                '• "bayar listrik 350rb"\n'
                '• "transfer BCA ke GoPay 100rb"\n\n'
                "💰 *Cek saldo & laporan*\n"
                '• "cek saldo" atau "total saldo"\n'
                '• "cek laporan" atau "laporan hari ini"\n'
                '• "laporan mingguan"\n'
                '• "analisa keuangan"\n'
                '• "cek budget"\n\n'
                "📅 *Tagihan, paylater, dan cicilan*\n"
                '• "cek tagihan"\n'
                '• "cek paylater"\n'
                '• "gopaylater mie gacoan 60115 jatuh tempo 1 juli 2026"\n'
                '• "netflix 65rb bulanan jatuh tempo tanggal 10"\n\n'
                "🤝 *Hutang*\n"
                '• "hutang" atau "cek hutang"\n'
                '• "hutang minggu ini"\n'
                '• "hutang telat"\n\n'
                "🎯 *Tanya keuangan & target*\n"
                '• "? berapa pengeluaran makan bulan ini"\n'
                '• "? cek target keuangan"\n\n'
                "📸 *Scan struk*\n"
                "• Kirim foto struk, nanti bot bantu baca dan catat.\n\n"
                "Tips: kalau salah catat, ikuti pertanyaan konfirmasi dari bot ya 👍"
            )
            return JSONResponse({
                "success": True,
                "message": "Help menu generated",
                "reply_message": report_msg
             })
        
        if any(cmd in lower_msg for cmd in ["cek sisa saldo", "cek saldo", "sisa saldo", "total saldo", "saldo keluarga", "cek balance"]):
            report_msg = (
                format_family_balance_snapshot(db)
                if any(cmd in lower_msg for cmd in ["keluarga", "total saldo"])
                else format_account_balance_snapshot(db, default_user.id).replace("Sisa Saldo Terkait", "Sisa Saldo")
            )
            return JSONResponse({
                "success": True,
                "message": "Balance report generated",
                "reply_message": report_msg
            })

        if any(cmd in lower_msg for cmd in ["laporan hari ini", "cek laporan", "daily report", "share report", "share dashboard"]):
            report_msg = generate_daily_report(db, default_user.id)
            return JSONResponse({
                "success": True,
                "message": "Daily report generated",
                "reply_message": report_msg
            })

        if any(cmd in lower_msg for cmd in ["laporan mingguan", "pengeluaran minggu lalu", "cek minggu lalu", "weekly report"]):
            report_msg = generate_weekly_report(db, default_user.id)
            return JSONResponse({
                "success": True,
                "message": "Weekly report generated",
                "reply_message": report_msg
            })

        if any(cmd in lower_msg for cmd in ["cek budgeting", "info budget", "status budget", "sisa budget", "cek budget", "budget", "anggaran"]):
            report_msg = FinancialQnAService(db, default_user.id).process_question(message_text)
            return JSONResponse({
                "success": True,
                "message": "Budget report generated",
                "reply_message": report_msg
            })

        if any(cmd in lower_msg for cmd in ["analisa pengeluaran", "analisa keuangan", "analisis pengeluaran"]):
             report_msg = generate_monthly_analysis_report(db, default_user.id)
             return JSONResponse({
                 "success": True,
                 "message": "Analysis report generated",
                 "reply_message": report_msg
             })

        if any(cmd in lower_msg for cmd in ["agar bisa kaya", "advice keuangan", "saran keuangan", "apa yang harus saya lakukan"]):
             report_msg = generate_financial_advice_report(db, default_user.id)
             return JSONResponse({
                 "success": True,
                 "message": "Financial advice generated",
                 "reply_message": report_msg
             })

        if lower_msg.startswith("?") or any(cmd in lower_msg for cmd in ["cek target", "target keuangan", "cashflow", "arus kas"]):
            report_msg = FinancialQnAService(db, default_user.id).process_question(message_text.lstrip("? "))
            return JSONResponse({
                "success": True,
                "message": "Financial QnA generated",
                "reply_message": report_msg
            })

        # Debt / receivable intake must run before the generic transaction fallback.
        # Debt creation is a ledger note only; only settlement messages create real transactions.
        debt_intent = _parse_debt_intent(message_text, default_user, db)
        if debt_intent:
            intent = debt_intent["intent"]
            amount = float(debt_intent["amount"])
            counterparty = debt_intent["counterparty"]

            if intent == "create_debt":
                debtor = debt_intent["debtor"]
                creditor_user = debt_intent.get("creditor_user")
                debt = models.Debt(
                    user_id=debtor.id,
                    type=models.DebtType.PERSONAL,
                    creditor=creditor_user.username if creditor_user else _party_display(counterparty),
                    name=f"Hutang ke {_party_display(counterparty)}",
                    total_amount=Decimal(str(amount)),
                    remaining_amount=Decimal(str(amount)),
                    is_active=True,
                    creditor_user_id=creditor_user.id if creditor_user else None,
                    debtor_user_id=debtor.id,
                    notes=f"WhatsApp debt note: {message_text}",
                )
                db.add(debt)
                db.commit()
                db.refresh(debt)
                reply_msg = _format_debt_reply(
                    "✅ *Hutang Dicatat*",
                    counterparty,
                    amount,
                    remaining=debt.remaining_amount,
                ) + "\n• Saldo akun: tidak berubah"
                return JSONResponse({
                    "success": True,
                    "message": "Debt note created without balance mutation",
                    "debt_id": debt.id,
                    "reply_message": reply_msg,
                })

            if intent == "create_receivable":
                creditor_user = debt_intent["creditor_user"]
                debt = models.Debt(
                    user_id=creditor_user.id,
                    type=models.DebtType.PERSONAL,
                    creditor=creditor_user.username,
                    name=f"Piutang dari {_party_display(counterparty)}",
                    total_amount=Decimal(str(amount)),
                    remaining_amount=Decimal(str(amount)),
                    is_active=True,
                    creditor_user_id=creditor_user.id,
                    debtor_user_id=None,
                    notes=f"WhatsApp receivable note from {_party_display(counterparty)}: {message_text}",
                )
                db.add(debt)
                db.commit()
                db.refresh(debt)
                reply_msg = _format_debt_reply(
                    "✅ *Piutang Dicatat*",
                    counterparty,
                    amount,
                    remaining=debt.remaining_amount,
                ) + "\n• Saldo akun: tidak berubah"
                return JSONResponse({
                    "success": True,
                    "message": "Receivable note created without balance mutation",
                    "debt_id": debt.id,
                    "reply_message": reply_msg,
                })

            if intent == "pay_debt":
                payer = debt_intent["payer"]
                debt = _find_payable_debt(db, payer.id, counterparty)
                if not debt:
                    return JSONResponse({
                        "success": True,
                        "message": "Debt not found",
                        "reply_message": f"❌ Tidak ditemukan hutang aktif ke {_party_display(counterparty)}.",
                    })
                if Decimal(str(amount)) > Decimal(str(debt.remaining_amount or 0)):
                    return JSONResponse({
                        "success": True,
                        "message": "Overpayment rejected",
                        "reply_message": f"❌ Jumlah bayar ({_format_rp(amount)}) melebihi sisa hutang ({_format_rp(debt.remaining_amount)}).",
                    })
                account_id = _detect_or_default_account_id(message_text, payer.id, db)
                tx = crud.create_transaction(
                    db=db,
                    user_id=payer.id,
                    transaction_type=TransactionType.EXPENSE,
                    amount=amount,
                    category="Hutang",
                    description=f"Bayar hutang ke {_party_display(counterparty)}",
                    raw_input=message_text,
                    account_id=account_id,
                    tags="semi_essential",
                )
                ok, error = _apply_debt_settlement(db, debt, amount, tx.id, notes=f"WhatsApp payment: {message_text}")
                if not ok:
                    return JSONResponse({
                        "success": True,
                        "message": "Debt payment rejected",
                        "reply_message": f"❌ {error}",
                    })
                reply_msg = _format_debt_reply(
                    "✅ *Pembayaran Hutang Dicatat*",
                    counterparty,
                    amount,
                    remaining=debt.remaining_amount,
                    account_snapshot=format_account_balance_snapshot(db, payer.id, account_ids=[account_id] if account_id else None),
                )
                return JSONResponse({
                    "success": True,
                    "message": "Debt payment recorded",
                    "transaction_id": tx.id,
                    "debt_id": debt.id,
                    "reply_message": reply_msg,
                })

            if intent == "receive_payment":
                receiver = debt_intent["receiver"]
                debt = _find_receivable_debt(db, receiver.id, counterparty)
                if not debt:
                    return JSONResponse({
                        "success": True,
                        "message": "Receivable not found",
                        "reply_message": f"❌ Tidak ditemukan piutang aktif dari {_party_display(counterparty)}.",
                    })
                if Decimal(str(amount)) > Decimal(str(debt.remaining_amount or 0)):
                    return JSONResponse({
                        "success": True,
                        "message": "Overpayment rejected",
                        "reply_message": f"❌ Jumlah terima ({_format_rp(amount)}) melebihi sisa piutang ({_format_rp(debt.remaining_amount)}).",
                    })
                account_id = _detect_or_default_account_id(message_text, receiver.id, db)
                tx = crud.create_transaction(
                    db=db,
                    user_id=receiver.id,
                    transaction_type=TransactionType.INCOME,
                    amount=amount,
                    category="Pembayaran Hutang",
                    description=f"Terima pembayaran hutang dari {_party_display(counterparty)}",
                    raw_input=message_text,
                    account_id=account_id,
                    tags=None,
                )
                ok, error = _apply_debt_settlement(db, debt, amount, tx.id, notes=f"WhatsApp receive payment: {message_text}")
                if not ok:
                    return JSONResponse({
                        "success": True,
                        "message": "Receivable payment rejected",
                        "reply_message": f"❌ {error}",
                    })
                reply_msg = _format_debt_reply(
                    "✅ *Penerimaan Piutang Dicatat*",
                    counterparty,
                    amount,
                    remaining=debt.remaining_amount,
                    account_snapshot=format_account_balance_snapshot(db, receiver.id, account_ids=[account_id] if account_id else None),
                )
                return JSONResponse({
                    "success": True,
                    "message": "Receivable payment recorded",
                    "transaction_id": tx.id,
                    "debt_id": debt.id,
                    "reply_message": reply_msg,
                })

        # Natural-language recurring capture:
        # Accept messages like "gopaylater mie gacoan 60115 jatuh tempo 1 juli 2026"
        # without requiring #recurring / #due markers.
        extracted_due_date, matched_span = _extract_fixed_due_date(message_text)
        if extracted_due_date and _looks_like_recurring_natural(lower_msg):
            has_explicit_recurrence = any(keyword in lower_msg for keyword in [
                "#recurring", "#monthly", "bulanan", "monthly",
                "mingguan", "weekly", "harian", "daily",
                "tahunan", "yearly", "setahun", "setiap", "tiap", "custom"
            ])
            recurring_type = RecurrenceType.MONTHLY
            if any(keyword in lower_msg for keyword in ["setahun", "tahunan", "yearly"]):
                recurring_type = RecurrenceType.YEARLY
            elif any(keyword in lower_msg for keyword in ["custom", "setiap", "tiap"]):
                recurring_type = RecurrenceType.CUSTOM
            elif any(keyword in lower_msg for keyword in ["minggu", "weekly"]):
                recurring_type = RecurrenceType.WEEKLY
            elif any(keyword in lower_msg for keyword in ["hari", "daily"]):
                recurring_type = RecurrenceType.DAILY
            total_occurrences = None if has_explicit_recurrence else 1

            description = _build_recurring_description(message_text[:matched_span[0]] + " " + message_text[matched_span[1]:])
            amount = _extract_recurring_amount(message_text, matched_span)

            if amount is not None and description:
                recurring = crud_extended.create_recurring_transaction(
                    db=db,
                    user_id=default_user.id,
                    transaction_type=TransactionType.EXPENSE,
                    amount=amount,
                    category="Paylater",
                    description=description,
                    recurrence_type=recurring_type,
                    next_due_date=extracted_due_date,
                    total_occurrences=total_occurrences,
                )
                amount_str = f"{amount:,.0f}".replace(",", ".")
                due_str = _format_date_long_id(extracted_due_date)
                schedule_label = (
                    recurring.recurrence_type.value
                    if total_occurrences is None and recurring and getattr(recurring, 'recurrence_type', None)
                    else "sekali bayar"
                )
                return JSONResponse({
                    "success": True,
                    "message": "Recurring transaction created from natural language",
                    "reply_message": (
                        "✅ *Tagihan berhasil dicatat*\n\n"
                        f"• Nama: {description}\n"
                        f"• Nominal: Rp {amount_str}\n"
                        f"• Jatuh tempo: {due_str}\n"
                        f"• Jadwal: {schedule_label}"
                    )
                })

        # Generic transaction fallback: classify and record normal finance messages.
        user_cats = db.query(models.UserCategory).filter(
            models.UserCategory.user_id == default_user.id,
            models.UserCategory.is_active == True
        ).all()
        cat_names = [c.name for c in user_cats]
        cat_types = {c.name: c.type for c in user_cats}

        classified = classifier.classify_transaction(message_text, cat_names, category_types=cat_types)
        amount = classified.get("amount")
        if amount is None or float(amount) <= 0:
            return JSONResponse({
                "success": False,
                "message": "No valid amount detected",
                "reply_message": None
            })

        transaction_type = classified.get("type", TransactionType.EXPENSE)
        account_id = None
        destination_account_id = None
        balance_account_ids = []

        # Auto-link to recurring: check if this transaction matches an active recurring entry
        matched_recurring = _match_transaction_to_recurring(
            db, default_user.id,
            description=classified.get("description", ""),
            category=classified.get("category", ""),
            amount=float(amount) if amount else 0,
            transaction_type=transaction_type
        )

        if transaction_type == TransactionType.TRANSFER:
            account_id, destination_account_id, _dest_user_id = detect_accounts_from_text(
                message_text, default_user.id, db
            )
            balance_account_ids = [acc_id for acc_id in [account_id, destination_account_id] if acc_id]
        else:
            # If matched to recurring with predefined account, use that
            if matched_recurring and matched_recurring.account_id:
                account_id = matched_recurring.account_id
            else:
                account_id = detect_account_from_text(message_text, default_user.id, db)
            
            # If no account detected and this is a recurring payment, ask user to select
            if not account_id and matched_recurring:
                # Store pending confirmation
                _pending_account_confirmations[default_user.id] = {
                    "recurring_id": matched_recurring.id,
                    "amount": float(amount),
                    "category": classified.get("category") or "Lain-lain",
                    "description": classified.get("description") or message_text,
                    "type": transaction_type,
                    "raw_input": message_text,
                    "created_at": datetime.now(timezone.utc)
                }
                # Get user's accounts for the prompt
                accounts = db.query(models.Account).filter(
                    models.Account.user_id == default_user.id,
                    models.Account.is_active == True
                ).all()
                account_list = "\n".join([f"• {acc.name}" for acc in accounts])
                reply_msg = (
                    f"❓ *Pilih Akun*\n\n"
                    f"Untuk tagihan *{matched_recurring.description}* (Rp {matched_recurring.amount:,.0f}):\n\n"
                    f"Pilih akun yang tersedia:\n{account_list}\n\n"
                    f"Ketik nama akun yang ingin digunakan."
                )
                return JSONResponse({
                    "success": True,
                    "message": "Account selection required",
                    "reply_message": reply_msg
                })
            
            if account_id:
                balance_account_ids = [account_id]

        tx = crud.create_transaction(
            db=db,
            user_id=default_user.id,
            transaction_type=transaction_type,
            amount=float(amount),
            category=classified.get("category") or "Lain-lain",
            description=classified.get("description") or message_text,
            raw_input=message_text,
            account_id=account_id,
            destination_account_id=destination_account_id,
            tags=classified.get("tags"),
            recurring_id=matched_recurring.id if matched_recurring else None
        )

        # If linked to recurring, update its last_paid_at and advance next_due_date
        if matched_recurring:
            _update_recurring_after_payment(db, matched_recurring, tx.created_at)

        amount_str = f"Rp {tx.amount:,.0f}".replace(",", ".")
        type_labels = {
            TransactionType.EXPENSE: "Pengeluaran",
            TransactionType.INCOME: "Pemasukan",
            TransactionType.SAVING: "Tabungan",
            TransactionType.INVESTMENT: "Investasi",
            TransactionType.DEBT: "Hutang",
            TransactionType.TRANSFER: "Transfer",
        }
        type_label = type_labels.get(tx.type, tx.type.value if hasattr(tx.type, "value") else str(tx.type))
        reply_msg = (
            "✅ *Transaksi tercatat*\n\n"
            f"• Jenis: {type_label}\n"
            f"• Nominal: {amount_str}\n"
            f"• Kategori: {tx.category}\n"
            f"• Deskripsi: {tx.description}"
        )

        reply_msg = reply_msg + "\n\n" + format_account_balance_snapshot(
            db,
            default_user.id,
            account_ids=balance_account_ids or None
        )

        return JSONResponse({
            "success": True,
            "message": "Transaction created",
            "transaction_id": tx.id,
            "amount": float(tx.amount),
            "category": tx.category,
            "reply_message": reply_msg
        })

    except Exception as e:
        db.rollback()
        print(f"Failed to process WhatsApp webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


# ── Auto-link transaction to recurring ──────────────────────────────────────

def _match_transaction_to_recurring(
    db: Session, user_id: int,
    description: str, category: str, amount: float, transaction_type: TransactionType
):
    """Match a classified transaction to an active recurring entry.
    
    Tries fuzzy matching on description, amount proximity, and category.
    Returns the RecurringTransaction object or None.
    """
    if not description or amount <= 0:
        return None

    # Get active recurring transactions for this user matching the type
    active_recurring = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == user_id,
        models.RecurringTransaction.is_active == True,
        models.RecurringTransaction.type == transaction_type
    ).all()

    if not active_recurring:
        return None

    # Normalize the incoming description: strip leading #, "bayar", "beli", "byar"
    desc_lower = description.lower().strip()
    for prefix in ["#", "bayar ", "beli ", "byar ", "tambah ", "isi "]:
        if desc_lower.startswith(prefix):
            desc_lower = desc_lower[len(prefix):].strip()
            break

    # Try matching by recurring description first, then amount proximity
    candidates = []
    for rec in active_recurring:
        if not rec.description:
            continue
        rec_desc = rec.description.lower().strip()

        # Score: 0 = no match, higher = better match
        score = 0

        # Description match: check if one contains the other
        if desc_lower in rec_desc or rec_desc in desc_lower:
            # Full or strong containment = high score
            score += 3
            # Bonus if they're both long strings with significant overlap
            if len(desc_lower) >= 4 and len(rec_desc) >= 4:
                if desc_lower in rec_desc and len(desc_lower) / max(len(rec_desc), 1) > 0.5:
                    score += 2

        # Amount proximity: within Rp 2.000 tolerance
        if abs(float(rec.amount) - amount) <= 2000:
            score += 2

        # Category match (bonus)
        if rec.category and category and rec.category.lower() == category.lower():
            score += 1

        if score >= 3:  # Minimum: description match (3) OR amount proximity + something else
            candidates.append((score, rec))

    if not candidates:
        return None

    # Return the highest-scored match
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _update_recurring_after_payment(db: Session, recurring, paid_at):
    """Update recurring entry after a linked payment."""
    from datetime import timedelta

    # 1. Update last_paid_at
    recurring.last_paid_at = paid_at

    # 2. Decrement remaining_occurrences if set
    if recurring.remaining_occurrences is not None:
        recurring.remaining_occurrences -= 1
        if recurring.remaining_occurrences <= 0:
            recurring.is_active = False
            db.commit()
            db.refresh(recurring)
            return

    # 3. Advance next_due_date based on recurrence type
    old_due = recurring.next_due_date
    if recurring.recurrence_type == RecurrenceType.MONTHLY:
        # Advance by 1 month from old next_due
        month = old_due.month + 1
        year = old_due.year
        if month > 12:
            month -= 12
            year += 1
        try:
            recurring.next_due_date = old_due.replace(year=year, month=month)
        except ValueError:
            # Handle month-end overflow (e.g., Jan 31 -> Feb 28)
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            recurring.next_due_date = old_due.replace(year=year, month=month, day=min(old_due.day, last_day))
    elif recurring.recurrence_type == RecurrenceType.WEEKLY:
        recurring.next_due_date = old_due + timedelta(days=7)
    elif recurring.recurrence_type == RecurrenceType.DAILY:
        recurring.next_due_date = old_due + timedelta(days=1)
    elif recurring.recurrence_type == RecurrenceType.YEARLY:
        recurring.next_due_date = old_due.replace(year=old_due.year + 1)
    elif recurring.recurrence_type == RecurrenceType.CUSTOM and recurring.interval_days:
        recurring.next_due_date = old_due + timedelta(days=recurring.interval_days)

    db.commit()
    db.refresh(recurring)
