import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("GOOGLE_API_KEY")
if not key:
    print("No API Key found")
else:
    try:
        client = genai.Client(api_key=key)
        print("Listing models...")
        # The SDK usage might slightly differ, checking standard client methods
        # Based on SDK docs (or general knowledge), usually client.models.list()
        # But 'google-genai' SDK structure is client.models.list()
        for m in client.models.list():
            print(m.name)
    except Exception as e:
        print(f"Error: {e}")
