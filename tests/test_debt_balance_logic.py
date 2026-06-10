"""Regression tests for WhatsApp debt/receivable balance semantics.

Run inside finance_web container:
    cd /app && PYTHONPATH=/app python tests/test_debt_balance_logic.py

These tests use unique REGTEST_* counterparties, restore touched account balances,
and soft-delete/deactivate test artifacts in finally blocks.
"""

import json
import os
import time
import urllib.request
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal

BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
BUNDA_PHONE = "62895330565959"
GROUP_ID = "120363398239342501@g.us"
GROUP_NAME = "Happy Family 🥰"
RUN_ID = f"REGTEST_DEBT_{int(time.time())}"


def _fetchone(sql: str, params: dict[str, Any] | None = None):
    with SessionLocal() as db:
        return db.execute(text(sql), params or {}).mappings().first()


def _execute(sql: str, params: dict[str, Any] | None = None):
    with SessionLocal() as db:
        db.execute(text(sql), params or {})
        db.commit()


def _fetchone_commit(sql: str, params: dict[str, Any] | None = None):
    with SessionLocal() as db:
        row = db.execute(text(sql), params or {}).mappings().first()
        db.commit()
        return row


def _webhook(message: str) -> dict[str, Any]:
    payload = {
        "message": message,
        "sender": "Bunda",
        "sender_number": BUNDA_PHONE,
        "group_name": GROUP_NAME,
        "group_id": GROUP_ID,
        "timestamp": "2026-06-10T10:00:00+07:00",
        "message_id": f"{RUN_ID}-{abs(hash(message))}",
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/whatsapp/webhook",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Secret": WEBHOOK_SECRET,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _bunda_dompet():
    row = _fetchone(
        """
        SELECT a.id, a.balance
        FROM accounts a
        JOIN users u ON u.id = a.user_id
        WHERE u.username = 'Bunda' AND a.name = 'Dompet' AND a.is_active = true
        """
    )
    assert row, "Bunda Dompet account not found"
    return int(row["id"]), Decimal(str(row["balance"]))


def _restore_balance(account_id: int, balance: Decimal):
    _execute("UPDATE accounts SET balance = :balance WHERE id = :id", {"balance": balance, "id": account_id})


def _soft_cleanup(counterparty: str, account_id: int, original_balance: Decimal):
    # Restore account first so failed pre-fix runs do not leak balance mutations.
    _restore_balance(account_id, original_balance)
    like = f"%{counterparty}%"
    _execute(
        """
        UPDATE transactions
        SET is_deleted = true, deleted_at = now()
        WHERE raw_input ILIKE :like OR description ILIKE :like
        """,
        {"like": like},
    )
    _execute(
        """
        UPDATE debts
        SET is_active = false, remaining_amount = 0, updated_at = now(),
            notes = COALESCE(notes, '') || E'\nREGTEST cleanup'
        WHERE creditor ILIKE :like OR name ILIKE :like OR notes ILIKE :like
        """,
        {"like": like},
    )


def _active_debt(counterparty: str):
    return _fetchone(
        """
        SELECT id, user_id, creditor, name, total_amount, remaining_amount, is_active,
               creditor_user_id, debtor_user_id
        FROM debts
        WHERE is_active = true
          AND (creditor ILIKE :like OR name ILIKE :like OR notes ILIKE :like)
        ORDER BY id DESC
        LIMIT 1
        """,
        {"like": f"%{counterparty}%"},
    )


def _debt_by_counterparty(counterparty: str):
    return _fetchone(
        """
        SELECT id, user_id, creditor, name, total_amount, remaining_amount, is_active,
               creditor_user_id, debtor_user_id
        FROM debts
        WHERE creditor ILIKE :like OR name ILIKE :like OR notes ILIKE :like
        ORDER BY id DESC
        LIMIT 1
        """,
        {"like": f"%{counterparty}%"},
    )


def _transaction_count(message: str) -> int:
    row = _fetchone(
        "SELECT COUNT(*) AS n FROM transactions WHERE is_deleted = false AND raw_input = :raw_input",
        {"raw_input": message},
    )
    return int(row["n"])


def _create_test_debt(counterparty: str, amount: int, receivable: bool = False) -> int:
    if receivable:
        row = _fetchone_commit(
            """
            INSERT INTO debts (user_id, type, creditor, name, total_amount, remaining_amount,
                               is_active, creditor_user_id, notes, created_at)
            VALUES (2, 'PERSONAL', 'Bunda', :name, :amount, :amount,
                    true, 2, :notes, now())
            RETURNING id
            """,
            {
                "name": f"REGTEST piutang {counterparty}",
                "amount": amount,
                "notes": f"REGTEST receivable counterparty={counterparty}",
            },
        )
    else:
        row = _fetchone_commit(
            """
            INSERT INTO debts (user_id, type, creditor, name, total_amount, remaining_amount,
                               is_active, debtor_user_id, notes, created_at)
            VALUES (2, 'PERSONAL', :creditor, :name, :amount, :amount,
                    true, 2, :notes, now())
            RETURNING id
            """,
            {
                "creditor": counterparty,
                "name": f"REGTEST hutang ke {counterparty}",
                "amount": amount,
                "notes": f"REGTEST debt counterparty={counterparty}",
            },
        )
    assert row
    return int(row["id"])


def test_create_debt_without_changing_balance():
    account_id, initial = _bunda_dompet()
    counterparty = f"{RUN_ID}_create_note"
    message = f"bunda hutang 16k ke {counterparty}"
    try:
        response = _webhook(message)
        after = _bunda_dompet()[1]
        debt = _active_debt(counterparty)
        assert response.get("success") is True
        assert after == initial, f"debt note changed balance: before={initial}, after={after}"
        assert debt and Decimal(str(debt["remaining_amount"])) == Decimal("16000")
        assert _transaction_count(message) == 0, "debt creation must not create financial transaction"
    finally:
        _soft_cleanup(counterparty, account_id, initial)


def test_create_receivable_without_changing_balance():
    account_id, initial = _bunda_dompet()
    counterparty = f"{RUN_ID}_create_receivable"
    message = f"{counterparty} hutang 16k ke bunda"
    try:
        response = _webhook(message)
        after = _bunda_dompet()[1]
        debt = _active_debt(counterparty)
        assert response.get("success") is True
        assert after == initial, f"receivable note changed balance: before={initial}, after={after}"
        assert debt and Decimal(str(debt["remaining_amount"])) == Decimal("16000")
        assert _transaction_count(message) == 0, "receivable creation must not create financial transaction"
    finally:
        _soft_cleanup(counterparty, account_id, initial)


def test_full_debt_payment_reduces_balance_and_marks_lunas():
    account_id, initial = _bunda_dompet()
    counterparty = f"{RUN_ID}_full_payment"
    message = f"bunda bayar hutang 16k ke {counterparty} dari dompet"
    try:
        debt_id = _create_test_debt(counterparty, 16000)
        response = _webhook(message)
        after = _bunda_dompet()[1]
        debt = _debt_by_counterparty(counterparty)
        assert response.get("success") is True
        assert after == initial - Decimal("16000")
        assert debt and int(debt["id"]) == debt_id
        assert Decimal(str(debt["remaining_amount"])) == Decimal("0")
        assert debt["is_active"] is False
        assert _transaction_count(message) == 1
    finally:
        _soft_cleanup(counterparty, account_id, initial)


def test_partial_debt_payment_reduces_balance_and_keeps_remaining():
    account_id, initial = _bunda_dompet()
    counterparty = f"{RUN_ID}_partial_payment"
    message = f"bunda bayar hutang 10k ke {counterparty} dari dompet"
    try:
        debt_id = _create_test_debt(counterparty, 16000)
        response = _webhook(message)
        after = _bunda_dompet()[1]
        debt = _debt_by_counterparty(counterparty)
        assert response.get("success") is True
        assert after == initial - Decimal("10000")
        assert debt and int(debt["id"]) == debt_id
        assert Decimal(str(debt["remaining_amount"])) == Decimal("6000")
        assert debt["is_active"] is True
        assert _transaction_count(message) == 1
    finally:
        _soft_cleanup(counterparty, account_id, initial)


def test_balance_after_multiple_debt_notes_and_payments():
    account_id, initial = _bunda_dompet()
    debt_counterparty = f"{RUN_ID}_multi_debt"
    receivable_counterparty = f"{RUN_ID}_multi_receivable"
    create_debt_msg = f"bunda hutang 20k ke {debt_counterparty}"
    create_receivable_msg = f"{receivable_counterparty} hutang 15k ke bunda"
    pay_msg = f"bunda bayar hutang 5k ke {debt_counterparty} dari dompet"
    receive_msg = f"bunda terima pembayaran hutang 7k dari {receivable_counterparty} ke dompet"
    try:
        assert _webhook(create_debt_msg).get("success") is True
        assert _webhook(create_receivable_msg).get("success") is True
        assert _bunda_dompet()[1] == initial, "debt/receivable notes must not affect balance"

        assert _webhook(pay_msg).get("success") is True
        assert _webhook(receive_msg).get("success") is True
        after = _bunda_dompet()[1]
        assert after == initial + Decimal("2000"), f"expected net +2k, got {after - initial}"

        debt = _active_debt(debt_counterparty)
        receivable = _active_debt(receivable_counterparty)
        assert debt and Decimal(str(debt["remaining_amount"])) == Decimal("15000")
        assert receivable and Decimal(str(receivable["remaining_amount"])) == Decimal("8000")
    finally:
        _soft_cleanup(debt_counterparty, account_id, initial)
        _soft_cleanup(receivable_counterparty, account_id, initial)


if __name__ == "__main__":
    tests = [
        test_create_debt_without_changing_balance,
        test_create_receivable_without_changing_balance,
        test_full_debt_payment_reduces_balance_and_marks_lunas,
        test_partial_debt_payment_reduces_balance_and_keeps_remaining,
        test_balance_after_multiple_debt_notes_and_payments,
    ]
    for test in tests:
        test()
        print(f"✓ {test.__name__}")
    print("debt balance logic regression passed")
