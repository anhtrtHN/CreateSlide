
import os
import sys
from utils import suppress_console_output

def test_nuclear():
    print("Beginning Nuclear Test.")
    print("1. Console is ACTIVE. You should see this.")
    
    print("2. Activating Suppression...")
    suppress_console_output()
    
    print("3. This message should be INVISIBLE.")
    
    # Test fileno() presence (which caused previous crashes?)
    try:
        fd = sys.stdout.fileno()
        print(f"   (fileno() returned: {fd})")
        if fd < 0 and fd != -1: 
             # -1 is sometime valid for wrappers, but let's see. 
             # Actually os.open usually returns > 0.
             pass
    except Exception as e:
        # If fileno() is missing/fails, we fail
        exit(1)

    # Simulate writing to a "broken" stream object - but the FD is now devnull
    # so even if python flushes to FD 1, it goes to null.
    try:
        sys.stdout.write("4. Direct Write test.\n")
        sys.stdout.flush()
    except Exception as e:
        # If this crashes, the test fails
        # But we can't print the failure because stdout is dead!
        # We must exit with error code
        exit(1)

    # We can't actually print "Success" to the console because we killed it.
    # So we write a file to indicate success
    with open("nuclear_success.txt", "w") as f:
        f.write("Nuclear suppression worked. No crash occurred during write.")

if __name__ == "__main__":
    if os.path.exists("nuclear_success.txt"):
        os.remove("nuclear_success.txt")
    test_nuclear()
