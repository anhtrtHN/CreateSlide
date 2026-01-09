
import json

def try_parse(text):
    print(f"--- Parsing: ---")
    print(text)
    try:
        json.loads(text)
        print("Success")
    except json.JSONDecodeError as e:
        print(f"Error: {e}")

# Case 1: Unquoted keys (JS style)
text1 = """{
  title: "Test"
}"""
try_parse(text1)

# Case 2: Single quotes (Python dict style)
text2 = """{
  'title': 'Test'
}"""
try_parse(text2)

# Case 3: Trailing comma
text3 = """{
  "title": "Test",
}"""
try_parse(text3)
