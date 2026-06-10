"""
AI Debt Classifier for Indonesian Natural Language Processing
Handles debt, credit, installment, paylater, and credit card transactions
"""
import json
import re
from openai import OpenAI
import os
from datetime import datetime, timedelta
from app.db.models import DebtType

def get_openai_client():
    """Get OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

# Platform mapping for auto-detection
PAYLATER_PLATFORMS = {
    "kredivo": {"type": DebtType.PAYLATER, "creditor": "Kredivo"},
    "shopee": {"type": DebtType.PAYLATER, "creditor": "Shopee PayLater"},
    "spaylater": {"type": DebtType.PAYLATER, "creditor": "Shopee PayLater"},
    "akulaku": {"type": DebtType.PAYLATER, "creditor": "Akulaku"},
    "indodana": {"type": DebtType.PAYLATER, "creditor": "Indodana"},
    "atome": {"type": DebtType.PAYLATER, "creditor": "Atome"},
    "tokopedia": {"type": DebtType.PAYLATER, "creditor": "Tokopedia PayLater"},
}

CREDIT_CARD_PLATFORMS = {
    "bca": {"type": DebtType.CREDIT_CARD, "creditor": "BCA Credit Card"},
    "mandiri": {"type": DebtType.CREDIT_CARD, "creditor": "Mandiri Credit Card"},
    "bni": {"type": DebtType.CREDIT_CARD, "creditor": "BNI Credit Card"},
    "bri": {"type": DebtType.CREDIT_CARD, "creditor": "BRI Credit Card"},
    "cimb": {"type": DebtType.CREDIT_CARD, "creditor": "CIMB Niaga Credit Card"},
    "citibank": {"type": DebtType.CREDIT_CARD, "creditor": "Citibank Credit Card"},
    "hsbc": {"type": DebtType.CREDIT_CARD, "creditor": "HSBC Credit Card"},
}

from app.utils import parse_amount

def detect_platform(text: str) -> dict:
    """Detect paylater or credit card platform from text"""
    text_lower = text.lower()
    
    # Check paylater platforms
    for keyword, info in PAYLATER_PLATFORMS.items():
        if keyword in text_lower:
            return info
    
    # Check credit card platforms
    for keyword, info in CREDIT_CARD_PLATFORMS.items():
        if keyword in text_lower or f"kartu kredit {keyword}" in text_lower:
            return info
    
    # Check generic keywords
    if any(word in text_lower for word in ["paylater", "pay later", "cicilan online"]):
        return {"type": DebtType.PAYLATER, "creditor": None}
    
    if any(word in text_lower for word in ["kartu kredit", "credit card", "cc"]):
        return {"type": DebtType.CREDIT_CARD, "creditor": None}
    
    return None

def parse_date(text: str, reference_date: datetime = None) -> datetime:
    """Parse date from Indonesian text"""
    if not reference_date:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    
    # Handle relative dates
    if "hari ini" in text_lower or "today" in text_lower:
        return reference_date
    
    if "besok" in text_lower or "tomorrow" in text_lower:
        return reference_date + timedelta(days=1)
    
    if "kemarin" in text_lower or "yesterday" in text_lower:
        return reference_date - timedelta(days=1)
    
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
    
    # Try to extract date patterns (DD/MM/YYYY, DD-MM-YYYY, or natural language DD Month YYYY)
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        r'(?:(?:jatuh tempo|due|tempo|pada|tgl|tanggal)\s*)?(\d{1,2})\s+(januari|jan|februari|feb|maret|mar|april|apr|mei|juni|jun|juli|jul|agustus|agu|aug|september|sep|oktober|okt|november|nov|desember|des)\s+(\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3 and groups[0].isdigit() and len(groups[0]) == 4:
                    return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                elif len(groups) == 3 and groups[1].isdigit():
                    return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                else:
                    return datetime(int(groups[2]), month_map[groups[1].lower()], int(groups[0]))
            except ValueError:
                pass
    
    return None

def classify_debt(text: str) -> dict:
    """
    Classify debt-related natural language input
    Returns structured JSON with intent, confidence, debt data, and payment data
    """
    
    # Prepare the output structure
    output = {
        "intent": "unknown",
        "confidence": 0.0,
        "debt": {
            "name": None,
            "type": "personal",
            "creditor": None,
            "total_amount": None,
            "installment_amount": None,
            "tenor": None,
            "interest_rate": None,
            "start_date": None,
            "due_date": None,
            "currency": "IDR"
        },
        "payment": {
            "amount": None,
            "date": None,
            "source_account": None
        },
        "notes": None
    }
    
    text_lower = text.lower()
    
    # Detect platform first
    platform_info = detect_platform(text)
    if platform_info:
        output["debt"]["type"] = platform_info["type"].value
        if platform_info.get("creditor"):
            output["debt"]["creditor"] = platform_info["creditor"]
    
    # Determine intent based on keywords
    # Intent: pay_debt
    if any(word in text_lower for word in ["bayar", "lunasi", "lunas", "setor", "payment"]):
        output["intent"] = "pay_debt"
        output["confidence"] = 0.8
        
        # Extract payment amount
        amount = parse_amount(text)
        if amount > 0:
            output["payment"]["amount"] = int(amount)
            output["confidence"] = 0.9
        
        # Extract payment date
        payment_date = parse_date(text)
        if payment_date:
            output["payment"]["date"] = payment_date.strftime("%Y-%m-%d")
    
    # Intent: create_debt
    elif any(word in text_lower for word in ["hutang", "pinjam", "kredit", "cicilan", "paylater", "kartu kredit", "jatuh tempo", "tempo", "tagihan"]) or platform_info:
        output["intent"] = "create_debt"
        output["confidence"] = 0.8
        
        # Extract amount
        amount = parse_amount(text)
        if amount > 0:
            output["debt"]["total_amount"] = int(amount)
            output["confidence"] = 0.9
        
        # Extract creditor name (person name pattern: "ke/dari [Name]")
        creditor_pattern = r'(?:ke|dari|sama)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        creditor_match = re.search(creditor_pattern, text)
        if creditor_match and not platform_info:
            output["debt"]["creditor"] = creditor_match.group(1)
            output["debt"]["type"] = "personal"
        
        # Detect debt type from keywords if not already detected
        if not platform_info:
            if any(word in text_lower for word in ["motor", "mobil", "kendaraan"]):
                output["debt"]["type"] = "leasing"
                output["debt"]["creditor"] = "Leasing"
            elif any(word in text_lower for word in ["bank", "kpr", "rumah"]):
                output["debt"]["type"] = "bank"
            elif any(word in text_lower for word in ["tagihan", "listrik", "air", "internet", "pulsa"]):
                output["debt"]["type"] = "bill"
        
        # Extract tenor (e.g., "12 bulan", "24x", "2 tahun")
        tenor_patterns = [
            r'(\d+)\s*(?:bulan|bln|month)',
            r'(\d+)\s*x',
            r'(\d+)\s*(?:tahun|year)',
        ]
        for pattern in tenor_patterns:
            tenor_match = re.search(pattern, text_lower)
            if tenor_match:
                tenor = int(tenor_match.group(1))
                if "tahun" in pattern or "year" in pattern:
                    tenor *= 12
                output["debt"]["tenor"] = tenor
                
                # Calculate installment if we have total amount and tenor
                if output["debt"]["total_amount"] and tenor > 0:
                    output["debt"]["installment_amount"] = int(output["debt"]["total_amount"] / tenor)
                break
        
        # Extract due/start date
        due_date = parse_date(text)
        if due_date:
            output["debt"]["due_date"] = due_date.strftime("%Y-%m-%d")
            if output["confidence"] < 0.85:
                output["confidence"] = 0.85

        start_date = parse_date(text)
        if start_date and not output["debt"]["start_date"]:
            output["debt"]["start_date"] = start_date.strftime("%Y-%m-%d")

    # Intent: update_debt
    elif any(word in text_lower for word in ["ubah", "update", "ganti", "edit"]):
        output["intent"] = "update_debt"
        output["confidence"] = 0.7
    
    # If we still have unknown intent but detected some debt-related info, assume create_debt
    if output["intent"] == "unknown" and (output["debt"]["total_amount"] or output["debt"]["creditor"]):
        output["intent"] = "create_debt"
        output["confidence"] = 0.6
    
    # Use OpenAI for better classification if available
    client = get_openai_client()
    if client and output["confidence"] < 0.9:
        try:
            prompt = f"""Kamu adalah AI Financial Assistant untuk menganalisis input bahasa Indonesia tentang HUTANG dan KREDIT.

Input: "{text}"

Tugas:
1. Tentukan intent: create_debt, pay_debt, update_debt, atau unknown
2. Ekstrak data hutang (nama, tipe, kreditor, jumlah, cicilan, tenor, bunga, tanggal)
3. Ekstrak data pembayaran jika ada (jumlah, tanggal, sumber)

Tipe hutang yang valid: personal, bank, leasing, credit_card, paylater, bill

Aturan:
- Jika data tidak disebutkan, isi dengan null
- Nominal selalu integer (1,2jt = 1200000)
- "bayar" = pay_debt intent
- "hutang/pinjam/kredit" = create_debt intent
- Detect platform: Kredivo/Shopee/Akulaku = paylater, BCA/Mandiri/BNI = credit_card

Kembalikan JSON persis seperti ini:
{{
  "intent": "create_debt | pay_debt | update_debt | unknown",
  "confidence": 0.0-1.0,
  "debt": {{
    "name": null,
    "type": "personal | bank | leasing | credit_card | paylater | bill",
    "creditor": null,
    "total_amount": null,
    "installment_amount": null,
    "tenor": null,
    "interest_rate": null,
    "start_date": null,
    "due_date": null,
    "currency": "IDR"
  }},
  "payment": {{
    "amount": null,
    "date": null,
    "source_account": null
  }},
  "notes": null
}}

Hanya kembalikan JSON, tanpa teks tambahan."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Financial Assistant. Selalu kembalikan hanya JSON yang valid."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if result_text.startswith("```"):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
            
            ai_result = json.loads(result_text)
            
            # Validate and merge with our result
            if ai_result.get("intent") in ["create_debt", "pay_debt", "update_debt", "unknown"]:
                # Use AI result but keep our parsed values if AI didn't find them
                output["intent"] = ai_result["intent"]
                output["confidence"] = ai_result.get("confidence", 0.8)
                
                # Merge debt data (prefer AI if not null, else keep ours)
                for key in output["debt"]:
                    if ai_result["debt"].get(key) is not None:
                        output["debt"][key] = ai_result["debt"][key]
                
                # Merge payment data
                for key in output["payment"]:
                    if ai_result["payment"].get(key) is not None:
                        output["payment"][key] = ai_result["payment"][key]
                
                if ai_result.get("notes"):
                    output["notes"] = ai_result["notes"]
                    
        except Exception as e:
            # Fallback to rule-based result if OpenAI fails
            pass
    
    # Ensure amounts are integers if present
    if output["debt"]["total_amount"]:
        output["debt"]["total_amount"] = int(output["debt"]["total_amount"])
    if output["debt"]["installment_amount"]:
        output["debt"]["installment_amount"] = int(output["debt"]["installment_amount"])
    if output["payment"]["amount"]:
        output["payment"]["amount"] = int(output["payment"]["amount"])
    
    return output
