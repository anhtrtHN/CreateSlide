
import os
import io
from dotenv import load_dotenv
from ai_engine import analyze_document
from slide_engine import create_pptx

# Load Env
load_dotenv()

pdf_path = r"C:\Users\admin\Downloads\RIBA Plan of Work 2020 Overview.pdf"
template_path = r"C:\Users\admin\Downloads\Temp. Beige Minimalistic Floral Pretty Portfolio Presentation.pptx"
output_path = "RIBA_Presentation.pptx"

print(f"Reading PDF: {pdf_path}")
try:
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
except Exception as e:
    print(f"Error reading PDF: {e}")
    exit(1)

print(f"Reading Template: {template_path}")
try:
    with open(template_path, "rb") as f:
        template_bytes = f.read()
except Exception as e:
    print(f"Error reading Template: {e}")
    exit(1)

print("Analyzing Document with AI (this may take a minute)...")
try:
    # Use "Chi tiết" mode for better test
    json_data = analyze_document(pdf_bytes, "application/pdf", detail_level="Chi tiết")
    print("AI Analysis Complete.")
    print("Generated JSON Title:", json_data.get("title"))
    print("Number of Slides:", len(json_data.get("slides", [])))
except Exception as e:
    print(f"AI Error: {e}")
    exit(1)

print("Generating PowerPoint...")
try:
    pptx_io = create_pptx(json_data, template_bytes)
    
    with open(output_path, "wb") as f:
        f.write(pptx_io.read())
        
    print(f"Success! Saved to: {os.path.abspath(output_path)}")
except Exception as e:
    print(f"Generation Error: {e}")
    exit(1)
