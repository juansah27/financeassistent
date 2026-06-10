"""
Receipt OCR service using multiple OCR providers:
1. OCR.Space API (free, no limit for personal use)
2. Google Cloud Vision API (free tier: 1000/month)
3. OpenAI Vision API (paid, fallback)
Supports receipts, payment proofs, transfer confirmations, etc.
"""
from openai import OpenAI
import os
import base64
import re
from pathlib import Path
from datetime import datetime
import json
from app.utils import parse_amount

# Google Cloud Vision imports
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    print("Google Cloud Vision not available. Install with: pip install google-cloud-vision")

def get_openai_client():
    """Get OpenAI client instance (reloads API key from env each time)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        return None

def extract_text_with_ocr_space(image_path: str) -> str:
    """Extract text from image using OCR.Space API (free, no limit)"""
    api_key = os.getenv("OCR_SPACE_API_KEY", "helloworld")  # Default free API key
    
    try:
        import httpx
        
        # Read image
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # OCR.Space API endpoint
        url = "https://api.ocr.space/parse/image"

        data = {
            "apikey": api_key,
            # Don't specify language - let OCR.Space auto-detect
            "isOverlayRequired": False,
            "detectOrientation": True,
            "scale": True,
        }
        
        # Try Engine 2 first (better for receipts), then Engine 1 (legacy, more robust for "corrupted" errors)
        engines_to_try = [2, 1]
        
        for engine_id in engines_to_try:
            print(f"🔄 Trying OCR.Space Engine {engine_id}...")
            
            # Prepare data for this attempt
            current_data = data.copy()
            current_data["OCREngine"] = engine_id
            
            # Reset file pointer for retries
            files = {"file": ("image.jpg", image_data, "image/jpeg")}
            
            response = httpx.post(url, files=files, data=current_data, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            
            # Check OCR exit code
            exit_code = result.get("OCRExitCode")
            if exit_code != 1:
                error_message = result.get("ErrorMessage", f"OCR exit code: {exit_code}")
                print(f"⚠️ OCR.Space Engine {engine_id} failed: {error_message}")
                if engine_id == engines_to_try[-1]: # Last attempt
                    print("❌ All OCR.Space engines failed.")
                    return None
                continue # Try next engine
            
            # Extract text from response
            if result.get("ParsedResults"):
                parsed_result = result["ParsedResults"][0]
                # Try ParsedText first
                parsed_text = parsed_result.get("ParsedText", "")
                if parsed_text:
                    print(f"✅ OCR.Space extracted text ({len(parsed_text)} chars)")
                    return parsed_text
                
                # If ParsedText is empty, try TextOverlay
                if "TextOverlay" in parsed_result and "Lines" in parsed_result["TextOverlay"]:
                    lines = []
                    for line in parsed_result["TextOverlay"]["Lines"]:
                        if "LineText" in line:
                            lines.append(line["LineText"])
                    text = "\n".join(lines)
                    if text:
                        print(f"✅ OCR.Space extracted text from overlay ({len(text)} chars)")
                        return text
            
            # If we got here, success code but no text?
            print(f"⚠️ OCR.Space Engine {engine_id} returned no text")
            
        return None
        
    except Exception as e:
        print(f"OCR.Space API Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_google_vision_client():
    """Get Google Cloud Vision client instance"""
    if not GOOGLE_VISION_AVAILABLE:
        return None
    
    # Try API key first (simpler setup)
    api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
    if api_key:
        try:
            # For API key, we'll use REST API directly
            return {"api_key": api_key}
        except Exception as e:
            print(f"Failed to initialize Google Vision with API key: {e}")
    
    # Try service account JSON file
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        try:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            return vision.ImageAnnotatorClient(credentials=credentials)
        except Exception as e:
            print(f"Failed to initialize Google Vision with service account: {e}")
    
    return None

def extract_text_with_google_vision(image_path: str) -> str:
    """Extract text from image using Google Cloud Vision API"""
    client = get_google_vision_client()
    if not client:
        return None
    
    try:
        # Read image
        with open(image_path, "rb") as image_file:
            content = image_file.read()
        
        # If using API key, use REST API
        if isinstance(client, dict) and "api_key" in client:
            import httpx
            api_key = client["api_key"]
            
            # Encode image to base64
            image_base64 = base64.b64encode(content).decode('utf-8')
            
            # Call Google Cloud Vision API
            url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
            payload = {
                "requests": [{
                    "image": {
                        "content": image_base64
                    },
                    "features": [
                        {
                            "type": "TEXT_DETECTION",
                            "maxResults": 10
                        },
                        {
                            "type": "DOCUMENT_TEXT_DETECTION",
                            "maxResults": 10
                        }
                    ]
                }]
            }
            
            response = httpx.post(url, json=payload, timeout=10.0)
            
            # Check for errors
            if response.status_code == 403:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_message = error_data.get("error", {}).get("message", "API key tidak valid atau Cloud Vision API belum diaktifkan")
                raise Exception(f"Google Vision API 403: {error_message}")
            
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response
            full_text = ""
            if "responses" in result and len(result["responses"]) > 0:
                response_data = result["responses"][0]
                # Try DOCUMENT_TEXT_DETECTION first (better for receipts)
                if "fullTextAnnotation" in response_data:
                    full_text = response_data["fullTextAnnotation"].get("text", "")
                # Fallback to TEXT_DETECTION
                elif "textAnnotations" in response_data and len(response_data["textAnnotations"]) > 0:
                    full_text = response_data["textAnnotations"][0].get("description", "")
            
            return full_text
        else:
            # Use client library
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description
            
            return None
            
    except Exception as e:
        error_message = str(e)
        print(f"Google Vision OCR Error: {error_message}")
        import traceback
        traceback.print_exc()
        
        # Return error details for better handling
        if "403" in error_message or "Forbidden" in error_message:
            if "billing" in error_message.lower() or "billing to be enabled" in error_message.lower():
                return {
                    "error": "google_vision_billing_required",
                    "message": "Google Cloud Vision API memerlukan billing yang diaktifkan. Meskipun ada free tier 1000 requests/bulan, billing tetap harus diaktifkan. Silakan enable billing di Google Cloud Console.",
                    "details": error_message
                }
            else:
                return {
                    "error": "google_vision_forbidden",
                    "message": "Google Cloud Vision API tidak dapat diakses. Pastikan API key valid dan Cloud Vision API sudah diaktifkan.",
                    "details": error_message
                }
        elif "401" in error_message or "Unauthorized" in error_message:
            return {
                "error": "google_vision_unauthorized",
                "message": "Google Cloud Vision API key tidak valid.",
                "details": error_message
            }
        
        return None

def parse_receipt_text(text: str) -> dict:
    """Parse extracted text to extract transaction data"""
    if not text:
        return None
    
    text_upper = text.upper()
    result = {
        "merchant_name": "",
        "total_amount": 0,
        "date": None,
        "description": "",
        "items": [],
        "transaction_purpose": None,  # NEW: Field for TUJUAN TRANSAKSI
        "confidence": 0.8  # Google Vision doesn't provide confidence per field
    }
    
    # Extract amount - logic enhanced to handle "Nominal + Admin Fee" case
    # 1. Look for explicit TOTAL/GRAND TOTAL first
    total_patterns = [
        r'(?:TOTAL|JUMLAH|TOTAL\s+TAGIHAN|TOTAL\s+BAYAR)\s*[:]?\s*Rp\.?\s*([\d.,]+)',
        r'(?:TOTAL|JUMLAH|TOTAL\s+TAGIHAN|TOTAL\s+BAYAR)\s*[:]?\s*([\d.,]+)',
    ]
    
    # 2. Look for Nominal Transfer and Admin Fee components
    nominal_patterns = [
        r'(?:NOMINAL|NILAI|JUMLAH)\s*(?:TRANSFER|TRANSAKSI)?\s*[:]?\s*Rp\.?\s*([\d.,]+)',
        r'Rp\.?\s*([\d.,]+)',
    ]
    
    fee_patterns = [
        r'(?:BIAYA|ADMIN|FEE)\s*(?:ADMIN|ADM|BANK|TRANSAKSI)?\s*[:]?\s*Rp\.?\s*([\d.,]+)',
    ]

    explicit_total = 0
    calculated_total = 0
    nominal_amount = 0
    fee_amount = 0
    
    # Check for explicit total
    for pattern in total_patterns:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        for match in matches:
            val = parse_amount(match)
            if val > explicit_total:
                explicit_total = val
    
    # Check for nominal + fee if explicit total might be missing or under-detected
    for pattern in nominal_patterns:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        # Get max value found as potential nominal (avoiding small numbers like dates)
        current_max = 0
        for match in matches:
            val = parse_amount(match)
            if val > current_max:
                current_max = val
        if current_max > nominal_amount:
            nominal_amount = current_max
            
    for pattern in fee_patterns:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        for match in matches:
            val = parse_amount(match)
            if val > 0 and val < nominal_amount: # Fee is usually smaller than nominal
                fee_amount = val # Take the last/first found fee? Usually there's only one.
                break 

    # Logic to decide the final amount
    if explicit_total > 0:
        result["total_amount"] = explicit_total
    
    # Fallback or correction: If Nominal + Fee > Explicit Total (or Explicit Total is 0)
    # common in transfer receipts where there is NO "Total" line
    calculated_total = nominal_amount + fee_amount
    if calculated_total > explicit_total and calculated_total > 0:
         # Only override if the components distinctively add up
         # AND we are fairly sure (e.g., fee detected is reasonable < 50000 or < 10% of nominal?)
         result["total_amount"] = calculated_total
    elif result["total_amount"] == 0 and nominal_amount > 0:
         result["total_amount"] = nominal_amount
    
    # Extract date - look for patterns like "24/12/2025", "2025-12-24"
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY-MM-DD format
                    year, month, day = match.groups()
                else:  # DD-MM-YYYY format
                    day, month, year = match.groups()
                result["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
            except:
                pass
    
    # Extract transaction purpose - look for "TUJUAN TRANSAKSI" field
    lines = text.split('\n')
    purpose_patterns = [
        r'TUJUAN\s+TRANSAKSI[:\s]+(.+)',
        r'TUJUAN[:\s]+(.+)',
    ]
    
    for pattern in purpose_patterns:
        match = re.search(pattern, text_upper, re.IGNORECASE)
        if match:
            purpose_value = match.group(1).strip()
            # Clean up common suffixes
            purpose_value = re.sub(r'\s*Ref\s*\d+.*$', '', purpose_value, flags=re.IGNORECASE)
            if purpose_value and len(purpose_value) > 2:  # Minimum length check
                result["transaction_purpose"] = purpose_value
                break
    
    # Extract merchant name - look for bank names, store names
    merchant_keywords = [
        "BCA", "BRI", "BNI", "MANDIRI", "CIMB", "DANAMON",
        "TRANSFER", "M-TRANSFER", "E-TRANSFER",
        "BERHASIL", "SUKSES"
    ]
    
    for line in lines[:10]:  # Check first 10 lines
        line_upper = line.upper()
        for keyword in merchant_keywords:
            if keyword in line_upper:
                result["merchant_name"] = line.strip()
                break
        if result["merchant_name"]:
            break
    
    # Extract description - use first meaningful line
    for line in lines:
        line_clean = line.strip()
        if line_clean and len(line_clean) > 5:
            # Skip if it's just numbers or common header text
            if not re.match(r'^[\d\s\.Rp,:-]+$', line_clean):
                result["description"] = line_clean[:100]  # Limit to 100 chars
                break
    
    # Use full text as extracted_text for classifier
    result["extracted_text"] = text[:500]  # Limit to 500 chars
    
    return result

def extract_receipt_data_google_vision(image_path: str) -> dict:
    """Extract receipt data using Google Cloud Vision API"""
    text_result = extract_text_with_google_vision(image_path)
    
    # Check if it's an error response
    if isinstance(text_result, dict) and "error" in text_result:
        return text_result
    
    if not text_result:
        return None
    
    result = parse_receipt_text(text_result)
    return result

def extract_receipt_data_openai(image_path: str) -> dict:
    """Extract receipt data using OpenAI Vision API"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        # Read image and encode to base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract information from this receipt/image. This could be a payment receipt, transfer proof, or transaction confirmation.

Return JSON with:
{
    "merchant_name": "store/bank/recipient name",
    "total_amount": 123456,
    "date": "YYYY-MM-DD",
    "items": ["item1", "item2"],
    "description": "transaction description",
    "transaction_purpose": "purpose from receipt if available",
    "confidence": 0.95
}

Important:
- Extract amounts in Indonesian Rupiah (Rp)
- Look for keywords: "TOTAL", "TOTAL TAGIHAN", "JUMLAH", "TRANSFER", "BERHASIL", "ANGSURAN", "CICILAN"
- For TRANSFER receipts: if there is a "Nominal" and "Biaya Admin", SUM THEM UP for the total_amount.
- Example: Nominal Rp 100.000 + Biaya Rp 2.500 -> total_amount 102500.
- Extract date in format YYYY-MM-DD (look for "24/12/2025" format and convert)
- If date not found, use today's date
- merchant_name can be store name, bank name, recipient name, or transaction type (e.g., "BCA Transfer", "Angsuran Ke-7")
- description should summarize the transaction (e.g., "m-Transfer to NSC HANDIYANJUANSAH", "Angsuran Ke-7")
- **transaction_purpose**: Extract from "TUJUAN TRANSAKSI" field if present (e.g., "Lainnya", "Transfer Keluarga", "Pembayaran Belanja", "Investasi", "Donasi"). If not found, set to null."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=800
        )
        
        result_text = response.choices[0].message.content
        
        # Clean JSON response
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(result_text)
        return result
        
    except Exception as e:
        print(f"OpenAI OCR Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error details for better handling
        error_type = type(e).__name__
        error_message = str(e)
        
        # Check for specific OpenAI errors
        if "RateLimitError" in error_type or "429" in error_message or "quota" in error_message.lower():
            return {
                "error": "quota_exceeded",
                "message": "OpenAI API quota exceeded. Please check your billing and add credits.",
                "details": error_message
            }
        elif "NotFoundError" in error_type or "404" in error_message:
            return {
                "error": "model_not_found",
                "message": "OpenAI model not found. Please check model name.",
                "details": error_message
            }
        elif "AuthenticationError" in error_type or "401" in error_message:
            return {
                "error": "authentication_failed",
                "message": "OpenAI API authentication failed. Please check your API key.",
                "details": error_message
            }
        else:
            return {
                "error": "unknown_error",
                "message": f"OCR processing failed: {error_message}",
                "details": error_message
            }

def extract_receipt_data_ocr_space(image_path: str) -> dict:
    """Extract receipt data using OCR.Space API"""
    text = extract_text_with_ocr_space(image_path)
    
    if not text:
        print("⚠️ OCR.Space returned no text")
        return None
    
    print(f"📝 OCR.Space extracted text preview: {text[:100]}...")
    result = parse_receipt_text(text)
    
    if result:
        print(f"📊 OCR.Space parsed result: amount={result.get('total_amount')}, merchant={result.get('merchant_name')}")
    
    return result

def extract_receipt_data(image_path: str) -> dict:
    """
    Extract data from receipt image using multiple OCR providers:
    Priority changed for better accuracy:
    1. OpenAI Vision (Best accuracy/context understanding)
    2. Google Gemini (Free Tier, Comparable to OpenAI)
    3. Google Cloud Vision (High accuracy OCR)
    4. OCR.Space API (Free fallback)
    """
    # 1. Try OpenAI Vision FIRST (Most accurate for context)
    if get_openai_client():
        print("🔍 Attempting OCR with OpenAI Vision (Best Accuracy)...")
        openai_result = extract_receipt_data_openai(image_path)
        
        # If successful, return immediately
        if openai_result and not (isinstance(openai_result, dict) and "error" in openai_result):
            print("✅ OpenAI OCR successful")
            return openai_result
        elif isinstance(openai_result, dict) and "error" in openai_result:
             print(f"⚠️ OpenAI failed: {openai_result.get('error')}, trying next provider...")
    
    # 2. Try Google Gemini NEXT (Good Free Tier)
    if os.getenv("GOOGLE_API_KEY"):
         print("🔍 Attempting OCR with Google Gemini...")
         gemini_result = extract_receipt_data_gemini(image_path)
         if gemini_result and not (isinstance(gemini_result, dict) and "error" in gemini_result):
            print("✅ Google Gemini OCR successful")
            return gemini_result
         else:
             print("⚠️ Google Gemini returned no valid result, trying next...")

    # 3. Try Google Cloud Vision
    if get_google_vision_client():
        print("🔍 Attempting OCR with Google Cloud Vision...")
        google_result = extract_receipt_data_google_vision(image_path)
        
        # Check for errors
        if isinstance(google_result, dict) and "error" in google_result:
            print(f"⚠️ Google Vision error: {google_result.get('error')}")
        elif google_result and google_result.get("total_amount"):
            print("✅ Google Cloud Vision OCR successful")
            return google_result
        else:
            print("⚠️ Google Vision returned no valid amount, trying next...")
            
    # 4. Fallback to OCR.Space (Least accurate but free)
    print("🔍 Attempting OCR with OCR.Space API (Fallback)...")
    ocr_space_result = extract_receipt_data_ocr_space(image_path)
    
    if ocr_space_result:
         if ocr_space_result.get("total_amount"):
            print("✅ OCR.Space OCR successful")
            return ocr_space_result
         else:
            print("⚠️ OCR.Space extracted text but no amount found")
            
    return None

def extract_receipt_data_gemini(image_path: str) -> dict:
    """Extract receipt data using Google Gemini API"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
        
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        
        # Determine mime type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
             mime_type = "image/jpeg"
             
        # Try multiple model names for robustness
        # Added gemini-1.5-pro which sometimes works when flash fails in certain regions
        models_to_try = [
            'gemini-1.5-flash', 
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro',
            'gemini-pro-vision',
            'models/gemini-1.5-flash' # Explicit prefix try
        ]
        
        # Read image data first
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = None
        used_model = None
        
        prompt = """Extract information from this receipt/image. This could be a payment receipt, transfer proof, or transaction confirmation.

Return JSON with:
{
    "merchant_name": "store/bank/recipient name",
    "total_amount": 123456,
    "date": "YYYY-MM-DD",
    "items": ["item1", "item2"],
    "description": "transaction description",
    "transaction_purpose": "purpose from receipt if available",
    "confidence": 0.95
}

Important:
- Extract the FINAL TRANSACTION AMOUNT (Expense/Bill value).
- CRITICAL: Do NOT use values labeled as 'Tunai' (Cash), 'Kembali' (Change), or 'Cash'. These are NOT the expense amount.
- Example: If Total is 17.900 and Tunai is 50.000, value is 17900.
- For TRANSFER receipts: if there is a "Nominal" and "Biaya Admin", SUM THEM UP for the total_amount.
- Example: Nominal Rp 100.000 + Biaya Rp 2.500 -> total_amount 102500.
- Look for keywords: "Total", "Grand Total", "Jumlah Tagihan", "Total Bayar".
- Extract amounts in Indonesian Rupiah (Rp)
- merchant_name can be store name, bank name, recipient name
- description should summarize the transaction
- **transaction_purpose**: Extract from "TUJUAN TRANSAKSI" field if present (e.g., "Lainnya", "Transfer Keluarga", "Pembayaran Belanja", "Investasi", "Donasi"). If not found, set to null."""

        for model_name in models_to_try:
            try:
                print(f"🔄 Trying Gemini model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                response = model.generate_content([
                    {'mime_type': mime_type, 'data': image_data},
                    prompt
                ])
                used_model = model_name
                break # Success
            except Exception as e:
                print(f"⚠️ Model {model_name} failed: {e}")
                continue
                
        if not response:
            print("❌ All Gemini models failed.")
            return None
        
        result_text = response.text
        
        # Clean JSON response
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
        result = json.loads(result_text)
        return result
        
    except ImportError:
        print("⚠️ google-generativeai package not installed. Skipping Gemini.")
        return None
    except Exception as e:
        print(f"Gemini OCR Error: {e}")
        return {"error": "gemini_error", "message": str(e)}

def extract_transaction_from_image(image_path: str) -> dict:
    """
    Extract transaction data from image (receipt/payment proof)
    Returns: dict with amount, description, date, and extracted text
    """
    ocr_result = extract_receipt_data(image_path)
    if not ocr_result:
        return None
    
    # Check if OCR result contains an error
    if isinstance(ocr_result, dict) and "error" in ocr_result:
        return ocr_result
    
    # Extract text from OCR result for classifier
    extracted_text = ocr_result.get("extracted_text", "")
    if not extracted_text:
        # Build extracted text from other fields
        if ocr_result.get("merchant_name"):
            extracted_text += f"{ocr_result['merchant_name']} "
        if ocr_result.get("description"):
            extracted_text += f"{ocr_result['description']} "
        if ocr_result.get("items"):
            if isinstance(ocr_result["items"], list):
                extracted_text += " ".join(ocr_result["items"])
            else:
                extracted_text += str(ocr_result["items"])
    
    return {
        "amount": ocr_result.get("total_amount", 0),
        "description": ocr_result.get("description") or ocr_result.get("merchant_name", ""),
        "date": ocr_result.get("date"),
        "extracted_text": extracted_text.strip(),
        "merchant_name": ocr_result.get("merchant_name"),
        "transaction_purpose": ocr_result.get("transaction_purpose"),  # NEW: Pass transaction purpose
        "confidence": ocr_result.get("confidence", 0.0)
    }
