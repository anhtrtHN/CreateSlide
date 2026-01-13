import time
from summarizer import summarize_book_deep_dive
import os
from dotenv import load_dotenv

load_dotenv()

# Simulate a 2-page document (approx 1000 words)
dummy_text = "This is a test document. " * 200 # 1000 words roughly
file_bytes = dummy_text.encode('utf-8')

print("Starting Deep Dive Benchmark...")
start_time = time.time()

try:
    result = summarize_book_deep_dive(file_bytes, "text/plain")
    end_time = time.time()
    
    print(f"\nTotal Time: {end_time - start_time:.2f} seconds")
    print("Keys returned:", result.keys())

except Exception as e:
    print(f"Error: {e}")
