"""
Test file for debt classifier
Run this to test the debt/credit NLP classifier with various Indonesian inputs
"""
from app.ai import debt_classifier
import json

def print_result(text: str, result: dict):
    """Pretty print test result"""
    print(f"\n{'='*80}")
    print(f"INPUT: {text}")
    print(f"{'='*80}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()

def test_create_debt_examples():
    """Test create_debt intent examples"""
    print("\n" + "="*80)
    print("TESTING CREATE_DEBT INTENT")
    print("="*80)
    
    examples = [
        "Hutang ke Andi 3 juta",
        "Pinjam uang ke Bank BCA 50 juta",
        "Kredit motor 15jt 12 bulan",
        "Cicilan rumah 5 juta per bulan selama 20 tahun",
        "Pakai Kredivo 500 ribu buat belanja",
        "Shopee PayLater 1,2 juta",
        "Kartu kredit BCA 2 juta",
        "Akulaku 750 ribu",
        "Cicilan mobil 4 juta 36 bulan",
        "Hutang tagihan listrik 200 ribu",
    ]
    
    for example in examples:
        result = debt_classifier.classify_debt(example)
        print_result(example, result)

def test_pay_debt_examples():
    """Test pay_debt intent examples"""
    print("\n" + "="*80)
    print("TESTING PAY_DEBT INTENT")
    print("="*80)
    
    examples = [
        "Bayar cicilan motor 1,2jt",
        "Bayar Shopee PayLater hari ini",
        "Lunasi hutang ke Andi 3 juta",
        "Bayar kartu kredit BCA 500 ribu",
        "Setor cicilan rumah 5 juta",
        "Bayar Kredivo 250 ribu",
        "Bayar hutang 100 ribu",
    ]
    
    for example in examples:
        result = debt_classifier.classify_debt(example)
        print_result(example, result)

def test_edge_cases():
    """Test edge cases and ambiguous inputs"""
    print("\n" + "="*80)
    print("TESTING EDGE CASES")
    print("="*80)
    
    examples = [
        "Hutang",  # No amount
        "Bayar",  # No amount or context
        "3 juta",  # Amount only
        "Ke Andi",  # Name only
        "Kredivo",  # Platform only
        "Bayar 100 ribu",  # Pay without context
        "Hutang ke toko 50 ribu kemarin",  # With date
    ]
    
    for example in examples:
        result = debt_classifier.classify_debt(example)
        print_result(example, result)

def test_platform_detection():
    """Test platform auto-detection"""
    print("\n" + "="*80)
    print("TESTING PLATFORM DETECTION")
    print("="*80)
    
    examples = [
        "Kredivo 500 ribu",
        "Shopee PayLater 1 juta",
        "Akulaku 750 ribu",
        "Indodana 300 ribu",
        "Atome 200 ribu",
        "Kartu kredit BCA 2 juta",
        "CC Mandiri 1,5 juta",
        "BNI Credit Card 3 juta",
    ]
    
    for example in examples:
        result = debt_classifier.classify_debt(example)
        print_result(example, result)

def test_complex_inputs():
    """Test complex inputs with multiple data points"""
    print("\n" + "="*80)
    print("TESTING COMPLEX INPUTS")
    print("="*80)
    
    examples = [
        "Kredit motor Honda Beat 15 juta cicilan 12 bulan mulai hari ini",
        "Pinjam ke Bank Mandiri 100 juta tenor 5 tahun bunga 8 persen",
        "Hutang ke Budi 5 juta jatuh tempo besok",
        "Pakai Shopee PayLater 1,2 juta buat beli laptop cicilan 3 bulan",
    ]
    
    for example in examples:
        result = debt_classifier.classify_debt(example)
        print_result(example, result)

def validate_schema(result: dict) -> bool:
    """Validate that result matches the expected schema"""
    required_keys = ["intent", "confidence", "debt", "payment", "notes"]
    debt_keys = ["name", "type", "creditor", "total_amount", "installment_amount", 
                 "tenor", "interest_rate", "start_date", "due_date", "currency"]
    payment_keys = ["amount", "date", "source_account"]
    
    # Check top-level keys
    if not all(key in result for key in required_keys):
        return False
    
    # Check debt keys
    if not all(key in result["debt"] for key in debt_keys):
        return False
    
    # Check payment keys
    if not all(key in result["payment"] for key in payment_keys):
        return False
    
    # Check intent values
    if result["intent"] not in ["create_debt", "pay_debt", "update_debt", "unknown"]:
        return False
    
    # Check debt type values
    valid_types = ["personal", "bank", "leasing", "credit_card", "paylater", "bill"]
    if result["debt"]["type"] not in valid_types:
        return False
    
    # Check confidence is between 0 and 1
    if not (0 <= result["confidence"] <= 1):
        return False
    
    return True

def test_schema_validation():
    """Test that all outputs conform to the required schema"""
    print("\n" + "="*80)
    print("VALIDATING OUTPUT SCHEMA")
    print("="*80)
    
    test_inputs = [
        "Hutang ke Andi 3 juta",
        "Bayar Shopee PayLater 1 juta",
        "Kredivo 500 ribu",
        "Bayar cicilan motor 1,2jt",
    ]
    
    all_valid = True
    for test_input in test_inputs:
        result = debt_classifier.classify_debt(test_input)
        is_valid = validate_schema(result)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{status}: {test_input}")
        if not is_valid:
            all_valid = False
            print(f"  Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    print(f"\n{'='*80}")
    if all_valid:
        print("✓ ALL OUTPUTS CONFORM TO SCHEMA")
    else:
        print("✗ SOME OUTPUTS DO NOT CONFORM TO SCHEMA")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DEBT CLASSIFIER TEST SUITE")
    print("="*80)
    
    # Run all tests
    test_create_debt_examples()
    test_pay_debt_examples()
    test_edge_cases()
    test_platform_detection()
    test_complex_inputs()
    test_schema_validation()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")
