
import json
from ai_engine import robust_json_parse

def test_robust_json():
    test_cases = [
        # 1. Standard JSON with double quotes
        ('{"title": "Valid"}', {'title': 'Valid'}, "Standard JSON"),
        
        # 2. Python Dict style (single quotes) - This matches the User's likely error source
        ("{'title': 'Valid'}", {'title': 'Valid'}, "Python Dict / Single Quotes"),
        
        # 3. Trailing Comma
        ('{"title": "Valid",}', {'title': 'Valid'}, "Trailing Comma"),
        
        # 4. Unquoted keys (JS Style) - Adding this capability
        ('{title: "Valid"}', {'title': 'Valid'}, "Unquoted Keys"),
        
        # 5. Markdown block wrapping
        ('```json\n{"title": "Valid"}\n```', {'title': 'Valid'}, "Markdown Block"),
        
        # 6. Garbage text around JSON
        ('Some prefix text... {"title": "Valid"} ... some suffix', {'title': 'Valid'}, "Embedded JSON"),
    ]
    
    passes = 0
    failures = 0
    
    print("Running JSON Robustness Tests...\n")
    
    for input_str, expected, name in test_cases:
        try:
            result = robust_json_parse(input_str)
            if result == expected:
                print(f"[PASS] {name}")
                passes += 1
            else:
                print(f"[FAIL] {name}")
                print(f"  Input: {input_str}")
                print(f"  Got: {result}")
                print(f"  Exp: {expected}")
                failures += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failures += 1

    print(f"\nSummary: {passes}/{len(test_cases)} passed.")
    
    if failures > 0:
        exit(1)

if __name__ == "__main__":
    test_robust_json()
