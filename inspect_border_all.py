import mesop as me
try:
    print(f"Type of me.Border.all: {type(me.Border.all)}")
    print(f"Is callable? {callable(me.Border.all)}")
except Exception as e:
    print(f"Error accessing me.Border.all: {e}")

try:
    b = me.Border(top=me.BorderSide(width=1))
    print("me.Border(top=...) worked")
except Exception as e:
    print(f"me.Border(top=...) failed: {e}")
