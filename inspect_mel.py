import mesop.labs as mel
import mesop as me

print("Check mel:")
for item in dir(mel):
    if "download" in item.lower():
        print(f"Found in mel: {item}")

print("\nCheck me.link:")
# Check if we can just print dir of me.link or me.native...
try:
    print(dir(me.link))
except:
    pass
