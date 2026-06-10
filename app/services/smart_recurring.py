from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import json
from app.db import models, crud_extended
from app.tasks.recurring import calculate_next_due_date
import difflib

def find_recurring_match(db: Session, user_id: int, transaction_description: str, transaction_amount: float):
    """
    Find a matching active recurring transaction for a manual payment.
    Matching criteria:
    1. Active status
    2. Name partial match (fuzzy or substring)
    3. Due date is in future (or slightly past, but not too far) - actually we want to catch ANY active one that hasn't been paid for this cycle
    """
    
    # Get all active recurring transactions for user
    recurring_list = crud_extended.get_recurring_transactions(db, user_id=user_id, active_only=True)
    
    best_match = None
    highest_score = 0
    
    # Clean transaction description: remove common keywords, special chars, and digits (optional)
    import re
    # Remove "bayar", "cicilan", "auto:", "via whatsapp", and everything in parens
    clean_desc = transaction_description.lower()
    clean_desc = re.sub(r'\(.*?\)', '', clean_desc) # Remove (via WhatsApp...)
    clean_desc = clean_desc.replace("bayar", "").replace("cicilan", "").replace("auto:", "")
    # Remove # and digits (often amounts like 100k)
    clean_desc = re.sub(r'[#\d]', '', clean_desc) 
    # Remove stand-alone amount suffixes that might remain (k, rb, jt, rp)
    # Since digits are gone, "100k" becomes "k". We look for these short tokens.
    clean_desc = re.sub(r'\b(k|rb|jt|rp)\b', '', clean_desc)
    clean_desc = " ".join(clean_desc.split()) # Normalize whitespace
    
    for recur in recurring_list:
        # 1. Name Match
        recur_desc_clean = recur.description.lower().replace("auto:", "").strip()
        recur_desc_clean = re.sub(r'[#\d]', '', recur_desc_clean) # Clean recurring name too
        recur_desc_clean = " ".join(recur_desc_clean.split())
        
        # Calculate similarity score using difflib
        # SequenceMatcher ratio returns 0.0 to 1.0, wait normalize to 0-100
        matcher = difflib.SequenceMatcher(None, clean_desc, recur_desc_clean)
        
        # Check if one is substring of another for higher base score
        if clean_desc in recur_desc_clean or recur_desc_clean in clean_desc:
            base_score = 80
        else:
            base_score = matcher.ratio() * 100
            
        score = base_score
        
        # Boost score if amount is similar (within 5% difference)
        recur_amount = float(recur.amount)
        amount_diff = abs(recur_amount - float(transaction_amount))
        if amount_diff <= (recur_amount * 0.05):
            score += 20
            
        # Check if score is high enough (threshold 80)
        if score >= 80 and score > highest_score:
            highest_score = score
            best_match = recur
            
    return best_match

def create_pending_confirmation(db: Session, user_id: int, transaction_id: int, recurring_id: int):
    """Create a pending confirmation record"""
    # Expire in 1 hour
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    pending = models.PendingConfirmation(
        user_id=user_id,
        transaction_id=transaction_id,
        recurring_id=recurring_id,
        action_type="update_recurring",
        expires_at=expires_at
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    return pending

def confirm_recurring_update(db: Session, pending_id: int):
    """Execute the update when user confirms 'Ya'"""
    pending = db.query(models.PendingConfirmation).filter(models.PendingConfirmation.id == pending_id).first()
    if not pending:
        return False, "Konfirmasi tidak ditemukan atau sudah kadaluarsa."
        
    recurring = db.query(models.RecurringTransaction).filter(models.RecurringTransaction.id == pending.recurring_id).first()
    if not recurring:
        return False, "Jadwal recurring tidak ditemukan."
        
    # Calculate next due date
    current_due = recurring.next_due_date
    if current_due.tzinfo is None:
        current_due = current_due.replace(tzinfo=timezone.utc)
        
    next_due = calculate_next_due_date(
        current_due,
        recurring.recurrence_type,
        recurring.day_of_month,
        recurring.interval_days
    )
    
    # Calculate early payment days
    now = datetime.now(timezone.utc)
    # Ensure current_due is timezone-aware for comparison
    if current_due.tzinfo is None:
        current_due_compare = current_due.replace(tzinfo=timezone.utc)
    else:
        current_due_compare = current_due
        
    days_diff = (current_due_compare.date() - now.date()).days
    
    # Generate Note/Tips (Updated phrasing)
    note_text = ""
    if days_diff > 0:
        note_text = f"ℹ️ *Info:* Pembayaran dilakukan {days_diff} hari lebih awal."
    elif days_diff < 0:
        note_text = f"ℹ️ *Info:* Pembayaran dilakukan {abs(days_diff)} hari setelah jatuh tempo."
    else:
        note_text = "ℹ️ *Info:* Pembayaran tepat waktu sesuai jatuh tempo."

    # Update recurring
    recurring.next_due_date = next_due
    recurring.last_paid_at = now
    
    # Handle remaining occurrences logic
    is_lunas = False
    remaining_text = ""
    if recurring.remaining_occurrences is not None and recurring.remaining_occurrences > 0:
        recurring.remaining_occurrences -= 1
        # Check if finished
        if recurring.remaining_occurrences == 0:
             recurring.is_active = False # Deactivate if done
             is_lunas = True
             remaining_text = "\n🎉 Cicilan LUNAS! Tidak ada jadwal pembayaran berikutnya 👍"
        else:
             remaining_text = f"\n📉 Sisa angsuran: {recurring.remaining_occurrences}x"
    
    # Link transaction if needed (optional, maybe update note)
    if pending.transaction_id:
        trx = db.query(models.Transaction).filter(models.Transaction.id == pending.transaction_id).first()
        if trx:
            trx.recurring_id = recurring.id
            trx.notes = (trx.notes or "") + f" [Linked to Recurring #{recurring.id}]"
            
    # Delete pending
    db.delete(pending)
    db.commit()
    
    # Format Response
    # Currency format with dots
    amount_str = f"{recurring.amount:,.0f}".replace(",", ".")
    
    msg = f"✅ *Pembayaran tercatat*\n\n📌 {recurring.description}\n💰 Rp {amount_str}"
    
    if is_lunas:
        msg += f"{remaining_text}\n\n{note_text}"
    else:
        msg += f"\n📅 Jadwal berikutnya: {next_due.strftime('%d %b %Y')}{remaining_text}\n\n{note_text}"
    
    return True, msg

def reject_recurring_update(db: Session, pending_id: int):
    """Execute rejection when user confirms 'Tidak'"""
    pending = db.query(models.PendingConfirmation).filter(models.PendingConfirmation.id == pending_id).first()
    if pending:
        db.delete(pending)
        db.commit()
    return True, "Konfirmasi dibatalkan. Jadwal recurring tidak berubah."
