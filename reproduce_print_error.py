
import sys
import io

def mock_safe_print_failure():
    # Simulate a stream that fails on flush
    class BrokenStream:
        def write(self, s):
            pass
        def flush(self):
            raise OSError(22, "Invalid argument")
    
    # Backup original stdout
    original_stdout = sys.stdout
    
    try:
        # 1. Test basic safe_print from utils
        from utils import safe_print
        print("Testing safe_print with normal stdout...")
        safe_print("Hello World")
        
        # 2. Inject broken stdout
        sys.stdout = BrokenStream()
        try:
            safe_print("This should crash")
            # Restore stdout to see the success message!
            sys.stdout = original_stdout
            print("Did not crash (Success!)")
        except BaseException as e:
            sys.stdout = original_stdout
            print(f"Failed: Crashed with {e}")
            
    except ImportError:
        print("Could not import utils")
    finally:
        sys.stdout = original_stdout

if __name__ == "__main__":
    mock_safe_print_failure()
