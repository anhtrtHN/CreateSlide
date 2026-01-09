import os
import sys

class LogFileStream:
    """
    A stream that redirects output to a log file instead of the console.
    This prevents Windows console crashes [Errno 22] while preserving logs.
    """
    def __init__(self, filename="app.log"):
        self.filename = filename
        # Ensure file exists and is empty/ready
        with open(self.filename, "a", encoding="utf-8") as f:
            pass
            
    def write(self, s):
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(s)
        except:
            pass
    
    def flush(self):
        try:
            # File flush happens on close of block above, but we can be explicit if needed
            pass
        except:
            pass
    
    def isatty(self):
        return False
        
    def fileno(self):
        # We can't easily give a real file descriptor for 'a' mode that stays open, 
        # but returning a valid dummy or opening devnull is safer for libraries checking this.
        try:
            return os.open(self.filename, os.O_RDWR | os.O_APPEND)
        except:
            return -1
        
    @property
    def encoding(self):
        return 'utf-8'
        
    def __getattr__(self, _):
        def dummy(*args, **kwargs):
            return None
        return dummy

def suppress_console_output():
    """
    Redirects stdout/stderr to app.log via Python patching.
    Explicitly deinits Colorama to prevent console crashes.
    """
    LOG_FILE = "app.log"
    
    # 0. Attempt to neutralize Colorama if present
    try:
        import colorama
        colorama.deinit()
    except:
        pass

    # 0.5. Neutralize CLICK (The source of banner crashes)
    try:
        import click
        def dummy_echo(*args, **kwargs):
            # Silently log to file if needed, or just ignore
            try:
                with open("app.log", "a", encoding="utf-8") as f:
                    f.write(str(args) + "\n")
            except:
                pass
        click.echo = dummy_echo
        click.secho = dummy_echo
    except:
        pass

    # 1. Python Level Silence -> Redirect to File
    sys.stdout = LogFileStream(LOG_FILE)
    sys.stderr = LogFileStream(LOG_FILE)

    # Note: We removed os.dup2 to avoid "Closed file" errors with click/flask.
    # By deiniting colorama, we hope to remove the main source of direct OS writes.

def safe_print(text: str):
    """
    Legacy helper. Does nothing.
    """
    pass
