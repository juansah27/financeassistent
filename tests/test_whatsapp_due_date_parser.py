from datetime import datetime
from zoneinfo import ZoneInfo

from app.routes.whatsapp import _extract_fixed_due_date, _format_date_long_id


def _long_date_for(message: str, reference_dt: datetime) -> str:
    due_date, span = _extract_fixed_due_date(message, reference_dt=reference_dt)
    assert span is not None, "expected parser to match due-date span"
    assert due_date is not None, "expected parser to return a due date"
    return _format_date_long_id(due_date)


reference_june = datetime(2026, 6, 10, 12, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
assert _long_date_for(
    "Shopee paylater beli mcd 119255 jatuh tempo tanggal 1 juli",
    reference_june,
) == "1 Juli 2026"
assert _long_date_for("kredivo 100rb jatuh tempo 1 juni", reference_june) == "1 Juni 2026"

reference_december = datetime(2026, 12, 10, 12, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
assert _long_date_for("tagihan 100rb jatuh tempo 1 januari", reference_december) == "1 Januari 2027"

print("whatsapp due-date parser regression passed")
