import json
import re
from openai import OpenAI
import os
from app.db.models import TransactionType
from app.utils import parse_amount

# ─── TAG MAPPING ────────────────────────────────────────────────────────────────
# Kolom `tags` di tabel transactions hanya menerima 3 nilai:
#   'essential'       — kebutuhan utama (makan dasar, rumah tangga, transport, utilitas)
#   'non_essential'   — keinginan/layanan tambahan (rokok, hiburan, shopping, donasi beauty)
#   'semi_essential'  — kredit/bill/cicilan
# Semua kategori lain → None (tidak di-tag).

ESSENTIAL_CATEGORIES = {
    "Rumah Tangga",
    "Transport",
    "Utilitas",
    "Kesehatan",
    "Internet",
    "Childcare",
}

NON_ESSENTIAL_CATEGORIES = {
    "Rokok",
    "Donasi",
    "Beauty & Personal Care",
    "Shopping",
    "Hiburan",
    "Arisan",
}

SEMI_ESSENTIAL_CATEGORIES = {
    "Kredit",
}

# Sub-kategori Konsumsi: kata kunci yang mengindikasikan "essential" vs "non_essential"
# Jika kata kunci *tidak* cocok dengan essential → fallback non_essential.
KONSUMSI_ESSENTIAL_KEYWORDS = [
    "nasi", "bakso", "mie", "batagor", "siomay", "siomai",
    "makroni", "macaroni", "tempe", "tahu", "pecel", "soto",
    "sayur", "martabak", "roti", "kue", "gorengan", "goreng",
    "baso", "sambal", "gado", "noodle", "rice",
]
KONSUMSI_NON_ESSENTIAL_KEYWORDS = [
    "kopi", "es ", "es-", "goodday", "pop ice", "cireng",
    "kacang", "cemilan", "snack", "jajanan", "pilus",
    "rokok", "sigaret", "cigarette", "sampoerna", "djarum",
    "susu", "milk", "teh", "tea", "jeruk", "orange",
    "chocolate", "coklat", "candy", "permen",
]


def category_to_tag(category: str, description: str = "") -> str | None:
    """
    Map a transaction category (and optional description) to one of the 3
    allowed tag values, or None if the category doesn't qualify for any tag.
    """
    if not category:
        return None

    cat = category.strip()

    if cat in ESSENTIAL_CATEGORIES:
        return "essential"

    if cat in NON_ESSENTIAL_CATEGORIES:
        return "non_essential"

    if cat in SEMI_ESSENTIAL_CATEGORIES:
        return "semi_essential"

    if cat == "Konsumsi":
        desc_lower = description.lower()
        # Check non-essential first (more specific keywords like 'kopi', 'es')
        for kw in KONSUMSI_NON_ESSENTIAL_KEYWORDS:
            if kw in desc_lower:
                return "non_essential"
        # Check essential (main meals)
        for kw in KONSUMSI_ESSENTIAL_KEYWORDS:
            if kw in desc_lower:
                return "essential"
        # Default Konsumsi → no tag (ambiguous)
        return None

    # Gaji, Bonus, Penjualan Aset, Transfer, Adjustment Income/Expense, etc.
    return None


def get_openai_client():
    """Get OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def load_keyword_mappings(db=None) -> dict:
    """Load keyword to category mappings from database"""
    should_close = False
    if not db:
        from app.db import session
        db_gen = session.get_db()
        db = next(db_gen)
        should_close = True
        
    try:
        from app.db.crud_keywords import get_all_keywords_with_category
        keywords = get_all_keywords_with_category(db)
        mapping = {k.keyword.lower(): k.category for k in keywords if k.category}
        return mapping
    except Exception as e:
        print(f"Error loading keyword mappings: {e}")
        return {}
    finally:
        if should_close:
            db.close()

def map_transaction_purpose_to_category(transaction_purpose: str, db=None) -> dict:
    """Map transaction purpose to category"""
    if not transaction_purpose:
        return None
    
    should_close = False
    if not db:
        from app.db import session
        db_gen = session.get_db()
        db = next(db_gen)
        should_close = True
    
    try:
        from app.db.crud_keywords import get_all_keywords_with_category
        keywords = get_all_keywords_with_category(db)
        purpose_lower = transaction_purpose.lower().strip()
        
        for kw in keywords:
            if kw.keyword.lower() == purpose_lower and kw.category:
                return {"category": kw.category}
        for kw in keywords:
            if kw.keyword.lower() in purpose_lower and kw.category:
                return {"category": kw.category}
        return None
    except Exception as e:
        print(f"Error mapping transaction purpose: {e}")
        return None
    finally:
        if should_close:
            db.close()

def clean_description(text: str) -> str:
    """Remove amounts from description"""
    cleaned = re.sub(r'\b\d+([.,]\d+)?\s*(k|rb|ribu|jt|juta|m|milyar|jt)?\b', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if len(cleaned) > 2 else text


def _keyword_match_position(text_lower: str, keyword: str) -> int | None:
    """Match category keywords on word boundaries to avoid 'emas' in 'pemasukan'."""
    kw = (keyword or "").strip().lower()
    if not kw:
        return None
    pattern = r'(?<!\w)' + re.escape(kw) + r'(?!\w)'
    match = re.search(pattern, text_lower)
    return match.start() if match else None


def _explicit_income_category(text_lower: str) -> str | None:
    """Detect user-explicit income before generic category keywords/AI."""
    income_keywords = [
        "pemasukan", "pendapatan", "income", "dapet", "dapat",
        "terima", "menerima", "diterima", "dikasih", "diberi",
    ]
    if not any(re.search(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', text_lower) for kw in income_keywords):
        return None

    if re.search(r'(?<!\w)(donasi|bantuan|orang tua|ortu)(?!\w)', text_lower):
        return "Donasi"
    if re.search(r'(?<!\w)(gaji|salary)(?!\w)', text_lower):
        return "Gaji"
    if re.search(r'(?<!\w)(bonus|thr)(?!\w)', text_lower):
        return "Bonus"
    return "Lain-lain"


def _tag_for_type(transaction_type: TransactionType, category: str, description: str) -> str | None:
    if transaction_type in [TransactionType.INCOME, TransactionType.TRANSFER]:
        return None
    return category_to_tag(category, description)


def classify_transaction(text: str, user_categories: list[str] = None, category_types: dict = None, transaction_purpose: str = None) -> dict:
    """Classify transaction using AI"""
    text_lower = text.lower()
    amount = parse_amount(text)
    
    # 0. Detect transfer keyword (no AI needed)
    transfer_keywords = ['transfer', 'pindah', 'pindahin', 'tarik', 'ambil', 'withdraw']
    if any(kw in text_lower for kw in transfer_keywords) and amount:
        desc = clean_description(text)
        return {
            "type": TransactionType.TRANSFER,
            "amount": amount,
            "category": "Transfer",
            "description": desc,
            "tags": _tag_for_type(TransactionType.TRANSFER, "Transfer", desc)
        }

    # 0b. Explicit income phrases must win over category keywords.
    explicit_income_category = _explicit_income_category(text_lower)
    if explicit_income_category and amount:
        desc = clean_description(text)
        return {
            "type": TransactionType.INCOME,
            "amount": amount,
            "category": explicit_income_category,
            "description": desc,
            "tags": _tag_for_type(TransactionType.INCOME, explicit_income_category, desc)
        }
    
    # 1. Check Keywords first
    try:
        keyword_map = load_keyword_mappings()
        matches = []
        for kw, map_cat in keyword_map.items():
            pos = _keyword_match_position(text_lower, kw)
            if pos is not None:
                matches.append((pos, len(kw), kw, map_cat))
        
        if matches:
            matches.sort(key=lambda x: (x[0], -x[1]))
            _, _, _, map_cat = matches[0]
            
            transaction_type = TransactionType.EXPENSE
            if category_types and map_cat in category_types:
                type_str = category_types[map_cat].upper()
                if "INCOME" in type_str: transaction_type = TransactionType.INCOME
                elif "SAVING" in type_str: transaction_type = TransactionType.SAVING
                elif "INVESTMENT" in type_str: transaction_type = TransactionType.INVESTMENT
                elif "DEBT" in type_str: transaction_type = TransactionType.DEBT
            
            desc = clean_description(text)
            return {
                "type": transaction_type,
                "amount": amount,
                "category": map_cat,
                "description": desc,
                "tags": _tag_for_type(transaction_type, map_cat, desc)
            }
    except Exception:
        pass

    prompt = (
        "Tipe: income, expense, saving, investment, debt, transfer\n"
        "Kategori: " + ", ".join(user_categories or []) + "\n"
        'Input: "' + text + '"\n'
        "Response JSON:\n"
        "{\n"
        "    \"type\": \"income|expense|saving|investment|debt|transfer\",\n"
        "    \"amount\": <number>,\n"
        "    \"category\": \"<category>\",\n"
        "    \"description\": \"<no-nominal desc>\",\n"
        "    \"debt_details\": {{\"is_internal\": true, \"debtor\": \"peminjam\", \"creditor\": \"pemberi\"}}\n"
        "}\n"
    )


    client = get_openai_client()
    if not client:
        desc = clean_description(text)
        return {"type": TransactionType.EXPENSE, "amount": amount, "category": "Lain-lain", "description": desc, "tags": None}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = json.loads(response.choices[0].message.content.strip().replace("```json", "").replace("```", ""))
        
        m = {"income": TransactionType.INCOME, "expense": TransactionType.EXPENSE, "saving": TransactionType.SAVING, "investment": TransactionType.INVESTMENT, "debt": TransactionType.DEBT, "transfer": TransactionType.TRANSFER}
        transaction_type = m.get(str(result.get("type", "")).lower(), TransactionType.EXPENSE)
        desc = result.get("description", clean_description(text))
        category = result.get("category", "Lain-lain")
        return {
            "type": transaction_type,
            "amount": float(result.get("amount", amount)),
            "category": category,
            "description": desc,
            "debt_details": result.get("debt_details"),
            "tags": _tag_for_type(transaction_type, category, desc)
        }
    except Exception:
        desc = clean_description(text)
        return {"type": TransactionType.EXPENSE, "amount": amount, "category": "Lain-lain", "description": desc, "tags": None}