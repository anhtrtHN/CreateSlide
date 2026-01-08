import mesop as me
import inspect

print("Inspect me.link args:")
try:
    print(inspect.signature(me.link))
except:
    print("Could not inspect signature")

print("\nCheck for me.html:")
print("html" in dir(me))
