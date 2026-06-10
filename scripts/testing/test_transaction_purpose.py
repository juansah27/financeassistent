"""
Test script for transaction purpose extraction
Tests the OCR service with the user's uploaded receipt image
"""
import sys
sys.path.insert(0, 'd:/Project/financeassistent')

from app.services.ocr import extract_transaction_from_image, parse_receipt_text

# Test with the uploaded image
image_path = r"C:\Users\Ladyqiu\.gemini\antigravity\brain\b7f3dd51-d6f0-4573-86ca-9d0b05bf03b4\uploaded_media_1770190859920.png"

print("=" * 80)
print("🧪 Testing Transaction Purpose Extraction")
print("=" * 80)
print(f"\n📂 Image: {image_path}\n")

# Test OCR extraction
print("🔍 Step 1: Extracting data from image...")
result = extract_transaction_from_image(image_path)

if result:
    print("\n✅ OCR Extraction Successful!\n")
    print(f"💰 Amount: Rp {result.get('amount', 0):,.2f}")
    print(f"📝 Description: {result.get('description', 'N/A')}")
    print(f"🏦 Merchant: {result.get('merchant_name', 'N/A')}")
    print(f"🎯 Transaction Purpose: {result.get('transaction_purpose', 'NOT DETECTED')}")
    print(f"📄 Extracted Text Preview:\n{result.get('extracted_text', 'N/A')[:200]}...")
    
    # Test classifier with transaction purpose
    if result.get('transaction_purpose'):
        print("\n" + "=" * 80)
        print("🔍 Step 2: Testing Classification with Transaction Purpose")
        print("=" * 80)
        
        from app.ai.classifier import classify_transaction, map_transaction_purpose_to_category
        
        # Test purpose mapping
        print(f"\n📌 Transaction Purpose: '{result.get('transaction_purpose')}'")
        
        purpose_mapping = map_transaction_purpose_to_category(result.get('transaction_purpose'))
        
        if purpose_mapping:
            print(f"✅ Mapped to Category: {purpose_mapping.get('category')}")
        else:
            print(f"❌ No mapping found in database keywords")
        
        # Test full classification
        print("\n🔍 Testing full classify_transaction()...")
        classified = classify_transaction(
            result.get('extracted_text', ''),
            transaction_purpose=result.get('transaction_purpose')
        )
        
        print(f"\n📊 Classification Result:")
        print(f"  Type: {classified.get('type')}")
        print(f"  Category: {classified.get('category')}")
        print(f"  Amount: Rp {classified.get('amount', 0):,.2f}")
        print(f"  Description: {classified.get('description')}")
        
        # Validate
        if 'transport' in classified.get('category', '').lower():
            print("\n❌ FAIL: Still categorized as Transport!")
        else:
            print("\n✅ SUCCESS: Not categorized as Transport!")
    else:
        print("\n⚠️ WARNING: Transaction Purpose not extracted from receipt")
        print("   This may be a regex pattern issue or OCR provider issue")
        
else:
    print("\n❌ OCR Extraction Failed!")
    print(f"Result: {result}")

print("\n" + "=" * 80)
print("✅ Test Complete")
print("=" * 80)
