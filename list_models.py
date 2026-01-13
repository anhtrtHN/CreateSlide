import os
from dotenv import load_dotenv
from google import genai
import sys

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found")
    sys.exit(1)

client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    for m in client.models.list():
        # Just print the name, assuming text generation is primary for flashes
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Error: {e}")
