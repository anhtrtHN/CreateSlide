
import os
import json
import time
import random
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
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.5-flash", 
        "gemini-3-flash-preview",
        "gemini-pro-latest"
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
        # Footer is at bottom, say y=30
        footer_y = 30
        # Copyright Text (Center Aligned looks better with Page Num on right, but user asked for Copyright ending symbol)
        # New Request: © 2026 Truong Tuan Anh | Document Summary
        c.drawString(margin, footer_y, "\u00A9 2026 Truong Tuan Anh | Document Summary")
        
        # Page Number (Right Aligned)
        page_num_text = f"Page {c.getPageNumber()}"
        c.drawRightString(width - margin, footer_y, page_num_text)
        c.restoreState()

    def check_page_break(current_y, font_name, font_size):
        # Check if we are too close to bottom (margin + footer space)
        # Footer is at 30, so let's stop at 60
        if current_y < 80: 
            draw_footer()
            c.showPage()
            current_y = height - header_margin
            c.setFont(font_name, font_size)
        return current_y

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
