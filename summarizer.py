
import os
import json
import time
import random
import concurrent.futures
from google import genai
from google.genai import types
from document_loader import load_document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Try to register a font that supports Vietnamese if possible
# Typically Arial or Times New Roman. 
# In a Windows environment, we might find them in Windows/Fonts
# For portability, we might need a bundled font, but for now let's try standard fonts.
# ReportLab standard fonts (Helvetica) don't support full Vietnamese unicode well without custom fonts.
# We will check common paths.

HAS_UNICODE_FONT = False
FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"

def register_fonts():
    global HAS_UNICODE_FONT
    if HAS_UNICODE_FONT: return # Already done

    if os.path.exists(FONT_PATH):
        try:
            # Check if already registered to avoid error
            from reportlab.pdfbase import pdfmetrics
            if 'Arial' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('Arial', FONT_PATH))
            HAS_UNICODE_FONT = True
        except:
            pass

SUMMARIZER_SYSTEM_INSTRUCTION = """
Bạn là một trợ lý AI chuyên nghiệp về tóm tắt văn bản. Nhiệm vụ của bạn là đọc nội dung tài liệu và tạo ra một bản tóm tắt súc tích, đầy đủ ý chính.

Cấu trúc bản tóm tắt mong muốn (trả về JSON):
{
  "title": "Tiêu đề tài liệu (hoặc tiêu đề đề xuất)",
  "overview": "Tóm tắt tổng quan (khoảng 100-200 từ)",
  "key_points": [
    "Điểm chính 1: ...",
    "Điểm chính 2: ...",
    "Điểm chính 3: ...",
    ...
  ],
  "conclusion": "Kết luận hoặc ý nghĩa chính rút ra."
}

Yêu cầu:
1. Ngôn ngữ: Tiếng Việt.
2. Văn phong: Chuyên nghiệp, khách quan.
3. Không bịa đặt thông tin không có trong tài liệu.
4. Đảm bảo JSON hợp lệ.
"""

# New Prompts for Deep Dive (Single Shot)
PROMPT_DEEP_DIVE_FULL = """
Please analyze the attached document and provide a comprehensive Deep Dive Summary.
Output the result strictly as a valid JSON object with the following keys:

1. "structure": A detailed table of contents with 2-sentence descriptions for each chapter.
2. "details": A highly detailed, chapter-by-chapter summary. Elaborate on arguments, case studies, and examples. Use markdown formatting (headings, bullets) within the string.
3. "synthesis": A synthesis section covering Core Framework, Critical Analysis, Actionable Insights (10 items), and Glossary.
4. "executive_overview": A final Executive Overview (approx. 1000 words) connecting all themes.

Language: Vietnamese.
Ensure the JSON is valid. Do not use markdown code blocks for the JSON output if possible, just the raw JSON string.
"""

def robust_json_parse(text):
    """Parses JSON robustly (reused logic)."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise

def summarize_document(file_bytes: bytes, mime_type: str, api_key: str = None, user_instructions: str = "") -> dict:
    """
    Summarizes the document using Gemini.
    Returns a dict with title, overview, key_points, conclusion.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Missing API Key.")

    client = genai.Client(api_key=key)
    parts = []
    
    # Construct base prompt
    base_prompt = "Hãy tóm tắt tài liệu này theo cấu trúc JSON đã yêu cầu."
    if user_instructions and user_instructions.strip():
        base_prompt += f"\n\nLƯU Ý CỦA NGƯỜI DÙNG (Cực kỳ quan trọng, hãy tuân thủ): {user_instructions}"

    # Check if PDF (Multimodal) or Text
    if mime_type == "application/pdf":
        parts.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))
        parts.append(types.Part.from_text(text=base_prompt))
    else:
        # Load text for DOCX/EPUB
        text_content = load_document(file_bytes, mime_type)
        full_prompt = f"Nội dung tài liệu:\n{text_content}\n\n{base_prompt}"
        parts.append(types.Part.from_text(text=full_prompt))

    models_to_try = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-flash-latest"
    ]
    
    last_exception = None
    for model_name in models_to_try:
        try:
            # print(f"Trying model: {model_name}...") 
            response = client.models.generate_content(
                model=model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    system_instruction=SUMMARIZER_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.5
                )
            )
            
            if not response.text:
                continue
                
            return robust_json_parse(response.text)
            
        except Exception as e:
            last_exception = e
            # Continue to next model
            time.sleep(1) # Brief pause
            continue
            
    raise ValueError(f"All models failed. Last error: {str(last_exception)}")

def save_summary_to_pdf(summary_data: dict, output_filename: str = "summary.pdf") -> str:
    """
    Generates a PDF file from the summary data.
    """
    register_fonts()
    c = canvas.Canvas(output_filename, pagesize=A4)
    width, height = A4
    
    # Margin
    margin = 50
    header_margin = 50
    y = height - header_margin
    
    # Font Settings
    title_font = 'Arial' if HAS_UNICODE_FONT else 'Helvetica'
    body_font = 'Arial' if HAS_UNICODE_FONT else 'Helvetica'
    
    def draw_footer():
        c.saveState()
        c.setFont(body_font, 10)
        footer_y = 30
        c.drawString(margin, footer_y, "\u00A9 2026 Truong Tuan Anh | Document Summary")
        page_num_text = f"Page {c.getPageNumber()}"
        c.drawRightString(width - margin, footer_y, page_num_text)
        c.restoreState()

    def check_page_break(current_y, font_name, font_size):
        if current_y < 80: 
            draw_footer()
            c.showPage()
            current_y = height - header_margin
            c.setFont(font_name, font_size)
        return current_y

    # Check for Deep Dive Mode
    if summary_data.get("mode") == "deep_dive":
        # 1. Title Page (Simple)
        c.setFont(title_font, 24)
        c.drawCentredString(width/2, height/2 + 50, "DEEP DIVE BOOK SUMMARY")
        c.setFont(body_font, 14)
        c.drawCentredString(width/2, height/2, "Generated by SlideGenius AI")
        c.showPage()
        y = height - header_margin

        sections = [
            ("Executive Overview", summary_data.get("executive_overview", "")),
            ("Structure & Outline", summary_data.get("structure", "")),
            ("Detailed Chapter Summaries", summary_data.get("details", "")),
            ("Synthesis & Analysis", summary_data.get("synthesis", ""))
        ]

        text_width = width - 2 * margin
        
        for sec_title, sec_content in sections:
            # Section Header
            y = check_page_break(y, title_font, 18)
            c.setFont(title_font, 18)
            c.drawString(margin, y, sec_title.upper())
            y -= 30
            
            # Content (Assuming Markdown-like text, but we treat as plain for now or remove basic markdown symbols)
            # Remove ```json ... ``` blocks if any leftovers, though here we get raw text
            clean_content = sec_content.replace("**", "").replace("##", "") 
            
            c.setFont(body_font, 12)
            lines = simpleSplit(clean_content, body_font, 12, text_width)
            
            for line in lines:
                y = check_page_break(y, body_font, 12)
                c.drawString(margin, y, line)
                y -= 18
            
            y -= 30 # Spacing between sections
            
        draw_footer()
        c.save()
        return os.path.abspath(output_filename)

    # Standard JSON Mode Rendering (Existing Code below...)

    # 1. Title
    c.setFont(title_font, 20)
    title = summary_data.get("title", "Document Summary")
    
    text_width = width - 2 * margin
    title_lines = simpleSplit(title, title_font, 20, text_width)
    
    for line in title_lines:
        y = check_page_break(y, title_font, 20)
        c.drawString(margin, y, line)
        y -= 30 
        
    y -= 20 
    
    # 2. Overview
    y = check_page_break(y, title_font, 14)
    c.setFont(title_font, 14)
    c.drawString(margin, y, "Tổng quan")
    y -= 25
    
    c.setFont(body_font, 12)
    overview = summary_data.get("overview", "")
    
    lines = simpleSplit(overview, body_font, 12, text_width)
    for line in lines:
        y = check_page_break(y, body_font, 12)
        c.drawString(margin, y, line)
        y -= 20
        
    y -= 20
    
    # 3. Key Points
    y = check_page_break(y, title_font, 14)
    c.setFont(title_font, 14)
    c.drawString(margin, y, "Điểm chính")
    y -= 25
    c.setFont(body_font, 12)
    
    key_points = summary_data.get("key_points", [])
    for point in key_points:
        bullet_point = f"- {point}"
        lines = simpleSplit(bullet_point, body_font, 12, text_width)
        for line in lines:
            y = check_page_break(y, body_font, 12)
            c.drawString(margin, y, line)
            y -= 20
        y -= 10 

    y -= 20
    
    # 4. Conclusion
    y = check_page_break(y, title_font, 14)
    c.setFont(title_font, 14)
    c.drawString(margin, y, "Kết luận")
    y -= 25
    c.setFont(body_font, 12)
    
    conclusion = summary_data.get("conclusion", "")
    lines = simpleSplit(conclusion, body_font, 12, text_width)
    for line in lines:
        y = check_page_break(y, body_font, 12)
        c.drawString(margin, y, line)
        y -= 20

    # Draw footer for the last page
    draw_footer()
    c.save()
    return os.path.abspath(output_filename)

def summarize_book_deep_dive(file_bytes: bytes, mime_type: str, api_key: str = None) -> dict:
    """
    Executes the 4-step deep dive summarization workflow.
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Missing API Key.")

    client = genai.Client(api_key=key)
    models_to_try = [
        "gemini-3.0-pro",   # Priority 1: Ultimate Model (2026)
        "gemini-3.0-flash", # Priority 2: Newest Flash
        "gemini-2.0-flash", # Priority 3: Previous Gen
        "gemini-1.5-pro",   # Priority 4: Old Pro
        "gemini-2.0-flash-lite"
    ]
    # Prepare Context
    parts = []
    if mime_type == "application/pdf":
        parts.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))
    elif mime_type == "text/plain":
         try:
            text_content = file_bytes.decode('utf-8')
         except:
            text_content = file_bytes.decode('latin-1') # Fallback
         parts.append(types.Part.from_text(text=f"Content:\n{text_content}"))
    else:
        text_content = load_document(file_bytes, mime_type)
        parts.append(types.Part.from_text(text=f"Content:\n{text_content}"))

    # Add the single shot prompt
    parts.append(types.Part.from_text(text=PROMPT_DEEP_DIVE_FULL))

    # Retry Logic with Model Fallback
    response_text = ""
    
    for model_name in models_to_try:
        print(f"Trying Deep Dive with model: {model_name}...")
        
        # Internal Retry for specific model (Rate Limits)
        model_retries = 3 # Reduce retries per model to failover faster
        initial_delay = 4
        
        success = False
        for attempt in range(model_retries):
            try:
                # Generate Content
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.5
                    )
                )
                if response.text:
                    response_text = response.text
                    print(f"Success with {model_name}.")
                    success = True
                    break
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    delay = initial_delay * (2 ** attempt)
                    print(f"[{model_name}] Rate limit hit. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                elif "NOT_FOUND" in error_str:
                     print(f"[{model_name}] Model not found. Skipping.")
                     break # Stop retrying this model, move to next
                else:
                    print(f"[{model_name}] Error: {e}")
                    # For other errors (overloaded, internal), try next attempt or next model
                    time.sleep(2)
        
        if success:
            break
            
    if not response_text:
        raise ValueError("Failed to retrieve response from all available Gemini models.")

    # Parse JSON
    try:
        data = robust_json_parse(response_text)
    except Exception as e:
        print(f"JSON Parsing Failed: {e}")
        print("Raw Output:", response_text[:200])
        raise ValueError("Could not parse Deep Dive JSON response.")

    print("Deep Dive Completed.")
    return {
        "mode": "deep_dive",
        "structure": data.get("structure", "N/A"),
        "details": data.get("details", "N/A"),
        "synthesis": data.get("synthesis", "N/A"),
        "executive_overview": data.get("executive_overview", "N/A")
    }

