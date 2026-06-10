
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append("d:/Project/financeassistent")

# Mock environment variables if needed (though they should be present in the shell)
# os.environ["OPENAI_API_KEY"] = "..." 

from app.services import ocr
from app.ai import classifier

def test_ocr():
    image_path = "/app/uploaded_media_1769324775716.png"
    
    print(f"Testing OCR on {image_path}")
    
    if not os.path.exists(image_path):
        print("Error: Image file not found")
        return

    # Mock extracted text since OCR API is flaky/timed out
    extracted_text = """m-Transfer:
BERHASIL
25/01/2026 14:04:41
1260895330565959
SHOPEE
SXXXXXX2
TOTAL TAGIHAN Rp. 107,600.00
Kirim ke sella
Biaya Termasuk PPN (Bila ada)
PT. BANK CENTRAL ASIA TBK.
MENARA BCA - JAKARTA PUSAT
NPWP : 0013084496091000"""

    print(f"\n--- Mocking OCR Result ---")
    
    # Test ocr.parse_receipt_text directly
    parsed_result = ocr.parse_receipt_text(extracted_text)
    print("\n--- Parsed Receipt Result ---")
    print(json.dumps(parsed_result, indent=2))
    
    # Test classifier
    print(f"\n--- Extracted Text for Classifier ---\n{extracted_text}")
    
    classification = classifier.classify_transaction(extracted_text)
    print("\n--- Classification Result ---")
    # Handle enum serialization for print
    cls_result = classification.copy()
    if hasattr(cls_result.get('type'), 'value'):
        cls_result['type'] = cls_result['type'].value
    print(json.dumps(cls_result, indent=2))

if __name__ == "__main__":
    test_ocr()
