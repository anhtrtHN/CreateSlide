import mesop as me
print("download" in dir(me))
# Search for anything download related
for item in dir(me):
    if "download" in item.lower():
        print(f"Found: {item}")
