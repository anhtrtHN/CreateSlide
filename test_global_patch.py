
import sys
import io
from utils import patch_io

def test_global_patch():
    print("1. Activating Global Patch...")
    patch_io()
    
    print("2. Patch Activated. Now injecting broken stream underlying the patch...")
    
    # Simulate a stream that fails on flush/write
    class BrokenStream:
        def write(self, s):
            if s.strip(): # unexpected error only on real content
               raise OSError(22, "Invalid argument")
        def flush(self):
            raise OSError(22, "Invalid argument")
    
    # We slip the broken stream UNDER the SafeStream wrapper
    # The SafeStream is now at sys.stdout
    if hasattr(sys.stdout, '_original'):
        sys.stdout._original = BrokenStream()
        print("   (Underlying stream broken successfully)")
    else:
        print("ERROR: Patch did not apply! sys.stdout is not SafeStream.")
        return

    print("3. Attempting to print (Should stay silent, NOT CRASH)...")
    try:
        print("This message should trigger the error but be swallowed.")
        sys.stdout.flush() # Explicit flush to trigger error
        
        # Restore for success message
        if hasattr(sys.stdout, '_original'):
             sys.stdout._original = sys.__stdout__
             
        print("4. SUCCESS: Execution continued past the error.")
    except Exception as e:
        # We have to restore stdout to see the failure message properly if possible
        sys.stdout = sys.__stdout__
        print(f"\nFAILURE: The application crashed with: {e}")
        exit(1)

if __name__ == "__main__":
    test_global_patch()
