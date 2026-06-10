"""
Utility functions for the application
"""
from datetime import datetime
from zoneinfo import ZoneInfo

# Default timezone for Indonesia (WIB)
DEFAULT_TIMEZONE = ZoneInfo("Asia/Jakarta")

def to_jakarta_time(dt: datetime) -> datetime:
    """
    Convert datetime to Jakarta timezone (WIB).
    If datetime is naive (no timezone), assumes UTC.
    Jinja2 filter: {{ dt | jakarta_time }}
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(DEFAULT_TIMEZONE)

def format_datetime_jakarta(dt: datetime, format_str: str = "%d/%m/%Y %H:%M") -> str:
    """
    Format datetime to Jakarta timezone with given format.
    Jinja2 filter: {{ dt | format_datetime_jakarta("%d/%m/%Y %H:%M") }}
    """
    if dt is None:
        return ""
    jakarta_dt = to_jakarta_time(dt)
    return jakarta_dt.strftime(format_str)

def now_jakarta() -> datetime:
    """
    Get current datetime in Jakarta timezone.
    """
    return datetime.now(DEFAULT_TIMEZONE)

 
import re



def parse_amount(text: str) -> float:
    """
    Robust amount parser that handles:
    - Indonesian format: 1.234.567,89 (dot=thousand, comma=decimal)
    - US/INTL format: 1,234,567.89 (comma=thousand, dot=decimal)
    - Mixed/Unknown: Auto-detect based on last separator
    - Currency symbols: Rp, $, etc are stripped
    - Suffixes: rb, k, jt, m, milyar are handled
    - Scans entire text for candidates and picks largest valid amount
    """
    if not text:
        return 0.0
        
    NUMBER_MAP = {
        "rb": 1000, "ribu": 1000, "k": 1000,
        "jt": 1000000, "juta": 1000000,
        "m": 1000000000, "milyar": 1000000000, "miliar": 1000000000,
    }

    # Pre-clean: strip currency symbols but keep text structure
    clean_text = text.lower().replace("rupiah", "").replace("rp", "").strip()
    
    # Iterate over all numeric patterns including potential suffixes
    # Pattern looks for digits possibly separated by . or , and optional suffix
    # Uses \b at END of suffix to prevent matching 'k' in 'kirim'
    # Leading \b removed to allow '5k' (no space/boundary between digit and k)
    regex = r'(\d+(?:[.,]\d+)*)(?:\s*(rb|ribu|k|jt|juta|m|milyar|miliar)\b)?'
    
    candidates = []

    for match in re.finditer(regex, clean_text):
        num_str = match.group(1)
        suffix = match.group(2)
        
        # Skip empty or standalone separators
        if not num_str or num_str in ['.', ',']:
            continue
            
        # Skip if purely numeric and too long (likely Transaction ID/Phone/NPWP)
        # e.g. 1260895330565959 (16 digits)
        # Threshold: 12 digits (hundreds of billions) is rare for personal finance without separators
        # But if it has separators (1.000.000.000) it's fine.
        is_flat_number = '.' not in num_str and ',' not in num_str
        if is_flat_number and len(num_str) > 12:
            continue
            
        # 1. Determine numeric value using heuristic
        val = 0.0
        val_str = num_str
        
        # Case A: Contains both . and ,
        if '.' in num_str and ',' in num_str:
            last_dot = num_str.rfind('.')
            last_comma = num_str.rfind(',')
            
            if last_comma > last_dot:
                # Indonesian/European: 1.234.567,89
                val_str = num_str.replace('.', '').replace(',', '.')
            else:
                # US/Intl: 1,234,567.89
                val_str = num_str.replace(',', '')
                
        # Case B: Contains only .
        elif '.' in num_str:
            if num_str.count('.') > 1:
                # 1.234.567 -> Thousand separator
                val_str = num_str.replace('.', '')
            elif re.search(r'\.\d{3}$', num_str):
                 # 1.000 -> Ambiguous. 
                 # Assumption: If suffix present (1.5 jt), dot is decimal.
                 if suffix: 
                     val_str = num_str
                 else:
                     val_str = num_str.replace('.', '') # 1.000 -> 1000
            else:
                # 10.5 -> Decimal
                val_str = num_str
                
        # Case C: Contains only ,
        elif ',' in num_str:
            if num_str.count(',') > 1:
                # 1,234,567 -> US thousand separator
                val_str = num_str.replace(',', '')
            elif re.search(r',\d{3}$', num_str):
                 # 1,000 -> US thousand
                 val_str = num_str.replace(',', '')
            else:
                 # 1,5 -> ID Decimal
                 val_str = num_str.replace(',', '.')

        try:
            val = float(val_str)
        except ValueError:
            continue
            
        # Apply multiplier
        mult = 1
        if suffix:
            mult = NUMBER_MAP.get(suffix.lower(), 1)
            
        final_val = val * mult
        
        candidates.append({
            "value": final_val,
            "has_multiplier": bool(suffix),
            "original": match.group(0)
        })
        
    if not candidates:
        return 0.0
        
    # Prioritization:
    # 1. Has multiplier (explicitly money usually)
    # 2. Value size (amounts usually larger than dates/quantities)
    candidates.sort(key=lambda x: (x["has_multiplier"], x["value"]), reverse=True)
    
    return candidates[0]["value"]
