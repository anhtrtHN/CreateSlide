
import os
import sys
from dotenv import load_dotenv
import summarizer
from unittest.mock import MagicMock

# Load env to get API Key
load_dotenv()

# Set console to utf-8 to avoid encoding errors
sys.stdout.reconfigure(encoding='utf-8')

def verify_instructions():
    print("Testing Summarizer with Instructions...")
    
    # Mock load_document to return text directly without needing a real file
    summarizer.load_document = MagicMock(return_value="Python là một ngôn ngữ lập trình mạnh mẽ.")
    
    # Instruction
    # We will use a dummy instruction. The key thing is that the function runs.
    instruction = "Hãy tóm tắt ngắn gọn."
    
    try:
        # Use a real API key check to ensure we don't fail on missing key
        if not os.environ.get("GOOGLE_API_KEY"):
            print("Skipping actual API call because GOOGLE_API_KEY is missing.")
            return

        result = summarizer.summarize_document(
            file_bytes=b"dummy", 
            mime_type="text/plain", # We mock the loader, so this type just needs to NOT be PDF
            user_instructions=instruction
        )
        
        print("\n--- Result ---")
        print(result)
        print("\nSuccess: Function executed without error.")
        
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    verify_instructions()
