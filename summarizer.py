
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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
import re

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
# New Prompts for Deep Dive (Single Shot)
# New Prompts for Deep Dive (Single Shot)
PROMPT_DEEP_DIVE_FULL = """
Hãy đóng vai một "Người Sưu Tầm Trí Tuệ" (Wisdom Collector) và tạo ra bản tóm tắt sách theo phong cách "Big Ideas" đầy cảm hứng.
Mục tiêu: Ngắn gọn, súc tích nhưng cực kỳ sâu sắc (More Wisdom in Less Time).

Bạn PHẢI trả về kết quả dưới dạng JSON hợp lệ với cấu trúc sau:

{
  "metadata": {
    "title": "Tên sách",
    "slogan": "Một câu slogan ngắn gọn hoặc mô tả thu hút về sách",
    "author": "Tên tác giả"
  },
  "big_ideas": [
    "Ý tưởng lớn 1 (3-5 từ, giật gân)",
    "Ý tưởng lớn 2...",
    ... (5-7 ý)"
  ],
  "introduction": {
    "text": "Đoạn giới thiệu 100-150 từ. Bối cảnh, tầm quan trọng, giọng văn hào hứng.",
    "best_quote": "Trích dẫn hay nhất hoặc bao quát nhất của cuốn sách"
  },
  "core_ideas": [
    {
      "title": "TÊN Ý TƯỞNG LỚN 1",
      "quote": "Trích dẫn nguyên văn đắt giá nhất liên quan đến ý tưởng này.",
      "commentary": "Phân tích chuyên sâu (200-300 từ): Đây là phần quan trọng nhất. Hãy viết thành một bài tiểu luận ngắn. 1. Giải thích cơ chế/nguyên lý của ý tưởng dưới góc độ khoa học/tâm lý học. 2. So sánh với các học thuyết khác. 3. Đưa ra ví dụ áp dụng cụ thể và các bẫy tư duy cần tránh. Tuyệt đối không viết sơ sài."
    },
    {
      "title": "TÊN Ý TƯỞNG LỚN 2",
      "quote": "...",
      "commentary": "Phân tích logic, mở rộng vấn đề, đào sâu vào bản chất (First Principles)."
    },
    ... (Tạo khoảng 5-7 ý tưởng cốt lõi)
    {
      "title": "TÊN Ý TƯỞNG LỚN CUỐI CÙNG - HÀNH ĐỘNG",
      "quote": "Trích dẫn về sự kiên trì/kỷ luật.",
      "commentary": "Kêu gọi hành động mạnh mẽ."
    }
  ],
  "about_author": "Tóm tắt tiểu sử tác giả ngắn gọn.",
  "about_creator": "SlideGenius AI: Chúng tôi cam kết chắt lọc những tinh hoa tri thức để giúp bạn tiết kiệm thời gian."
}

LƯU Ý:
- Ngôn ngữ: Tiếng Việt (trừ các tên riêng).
- Giọng văn: Truyền cảm hứng, sâu sắc, trực diện.
- JSON: Không được lỗi cú pháp.
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

    # Helper for basic Markdown -> ReportLab XML
    def markdown_to_xml(text):
        if not isinstance(text, str):
            import json
            text = json.dumps(text, ensure_ascii=False)
        
        # Escape basic XML chars first
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Replace **bold** with <b>bold</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Replace ## Headings with bold and breaks
        text = re.sub(r'##\s*(.*?)\n', r'<b>\1</b><br/>', text)
        
        # Replace lists
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                 processed_lines.append(f"&bull; {line[2:]}<br/>")
            elif line.startswith("* "): # alternative bullet
                 processed_lines.append(f"&bull; {line[2:]}<br/>")
            else:
                 processed_lines.append(line)
        
        return "<br/>".join(processed_lines)

    # Check for Deep Dive Mode
    if summary_data.get("mode") == "deep_dive":
        doc = SimpleDocTemplate(
            output_filename, 
            pagesize=A4,
            rightMargin=50, leftMargin=50, 
            topMargin=50, bottomMargin=50
        )
        
        styles = getSampleStyleSheet()
        # Custom Styles
        title_style = ParagraphStyle(
            'CustomTitle', 
            parent=styles['Title'], 
            fontName='Arial', 
            fontSize=26, 
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        slogan_style = ParagraphStyle(
            'CustomSlogan', 
            parent=styles['Normal'],
            fontName='Arial',
            fontSize=14,
            spaceAfter=24,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        header_style = ParagraphStyle(
            'CustomHeader', 
            parent=styles['Heading1'], 
            fontName='Arial', 
            fontSize=16, 
            spaceBefore=12, 
            spaceAfter=12,
            textColor=colors.black,
            borderPadding=5,
            backColor=colors.lightgrey
        )
        quote_style = ParagraphStyle(
            'CustomQuote', 
            parent=styles['Normal'], 
            fontName='Arial', 
            fontSize=12, 
            leading=18,
            leftIndent=20,
            rightIndent=20,
            spaceBefore=6,
            spaceAfter=6,
            textColor=colors.darkgreen,
            fontName_Italic='Arial',
            alignment=TA_JUSTIFY
        )
        body_style = ParagraphStyle(
            'CustomBody', 
            parent=styles['Normal'], 
            fontName='Arial', 
            fontSize=12, 
            leading=18, 
            spaceAfter=8,
            alignment=TA_JUSTIFY
        )
        
        from reportlab.platypus import KeepTogether

        story = []
        
        metadata = summary_data.get("metadata", {})
        doc_title = metadata.get("title", "BOOK SUMMARY")
        doc_author = metadata.get("author", "Unknown Author")
        doc_slogan = metadata.get("slogan", "More Wisdom in Less Time")
        
        # --- TITLE PAGE ---
        story.append(Spacer(1, 30))
        story.append(Paragraph("TUAN ANH'S NOTES", 
            ParagraphStyle('Brand', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=colors.grey)))
        story.append(Paragraph("More Wisdom in Less Time", 
            ParagraphStyle('SubBrand', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.grey)))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph(doc_title.upper(), title_style))
        story.append(Paragraph(doc_slogan, slogan_style))
        story.append(Paragraph(f"<b>By {doc_author}</b>", 
            ParagraphStyle('Author', parent=body_style, alignment=TA_CENTER, fontSize=12)))
        story.append(Spacer(1, 15))
        story.append(Paragraph("---", ParagraphStyle('Line', parent=body_style, alignment=TA_CENTER)))
        
        # --- THE BIG IDEAS ---
        story.append(Paragraph("THE BIG IDEAS (CÁC Ý TƯỞNG LỚN)", header_style))
        big_ideas = summary_data.get("big_ideas", [])
        if isinstance(big_ideas, list):
            for idea in big_ideas:
                story.append(Paragraph(f"&bull; <b>{idea}</b>", body_style))
        story.append(Spacer(1, 15))
        story.append(Paragraph("---", ParagraphStyle('Line', parent=body_style, alignment=TA_CENTER)))
        
        # --- INTRODUCTION ---
        intro_data = summary_data.get("introduction", {})
        story.append(Paragraph("GIỚI THIỆU", header_style))
        if intro_data.get("text"):
             story.append(Paragraph(intro_data["text"], body_style))
        
        if intro_data.get("best_quote"):
             story.append(Spacer(1, 8))
             story.append(Paragraph(f"<i>“{intro_data['best_quote']}”</i>", quote_style))
             story.append(Paragraph(f"— {doc_author}", 
                ParagraphStyle('QuoteAuthor', parent=body_style, alignment=TA_RIGHT, fontSize=10)))

        story.append(PageBreak())

        # --- CORE IDEAS ---
        core_ideas = summary_data.get("core_ideas", [])
        for idea in core_ideas:
            elements = []
            title = idea.get("title", "BIG IDEA")
            quote = idea.get("quote", "")
            commentary = idea.get("commentary", "")
            
            elements.append(Paragraph(title.upper(), 
                ParagraphStyle('IdeaTitle', parent=styles['Heading2'], fontName='Arial', fontSize=14, spaceBefore=6, textColor=colors.darkblue)))
            
            if quote:
                elements.append(Paragraph(f"<i>“{quote}”</i>", quote_style))
            
            if commentary:
                elements.append(Paragraph("<b>Comment:</b>", 
                    ParagraphStyle('AIHeader', parent=body_style, fontSize=10, textColor=colors.black, spaceBefore=4)))
                # Render HTML/XML formatting in commentary
                xml_commentary = markdown_to_xml(commentary)
                elements.append(Paragraph(xml_commentary, body_style))
                
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("---", ParagraphStyle('Line', parent=body_style, alignment=TA_CENTER)))
            elements.append(Spacer(1, 10))
            
            # Keep idea block together so it doesn't break awkwardly
            story.append(KeepTogether(elements))

        story.append(PageBreak())

        # --- ABOUT AUTHOR & CREATOR ---
        story.append(Paragraph("ABOUT THE AUTHOR (VỀ TÁC GIẢ)", header_style))
        story.append(Paragraph(summary_data.get("about_author", ""), body_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("ABOUT THE NOTE CREATOR (VỀ NGƯỜI TẠO NOTE)", header_style))
        story.append(Paragraph(summary_data.get("about_creator", ""), body_style))

        # --- FOOTER FUNCTION ---
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Arial', 9)
            canvas.setFillColor(colors.grey)
            
            # Left Footer: Copyright
            canvas.drawString(50, 20, "© 2026 Truong Tuan Anh | Document Summary")
            
            # Right Footer: Page Number
            page_num_text = f"Page {doc.page}"
            canvas.drawRightString(A4[0] - 50, 20, page_num_text)
            
            canvas.restoreState()

        # Build PDF with Footer
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
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
    
    # 1. Extensive Model List (Copied from ai_engine.py for consistency)
    base_models = [
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash", 
        "gemini-1.5-pro",
        "gemini-1.5-flash",
         # Fallbacks
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    ]
    models_to_try = base_models + ["gemini-flash-latest", "gemini-pro-latest"]
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

    # Retry Logic with Fast Failover (inspired by ai_engine.py)
    response_text = ""
    retry_count = 0
    success = False

    for model_name in models_to_try:
        try:
            print(f"Trying Deep Dive with model: {model_name}...")
            
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
            
            # Handling Rate Limits (429) & Resource Exhausted -> FAIL FAST & TRY NEXT
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                if "limit: 0" in error_str:
                     print(f"[{model_name}] Limit 0 (No Quota). Skipping...")
                     continue

                retry_count += 1
                wait_time = min(10, (1.5 ** retry_count)) 
                print(f"[{model_name}] Quota exceeded. Waiting {wait_time:.1f}s then trying NEXT model...")
                time.sleep(wait_time)
                continue # Skip to next model
            
            elif "NOT_FOUND" in error_str or "404" in error_str:
                 print(f"[{model_name}] Not found. Skipping...")
                 continue
            
            else:
                print(f"[{model_name}] Error: {str(e)}. Skipping...")
                continue
        
    if not success or not response_text:
        raise ValueError("Failed to retrieve response from all available Gemini models (Deep Dive).")

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
        "metadata": data.get("metadata", {}),
        "big_ideas": data.get("big_ideas", []),
        "introduction": data.get("introduction", {}),
        "core_ideas": data.get("core_ideas", []),
        "about_author": data.get("about_author", ""),
        "about_creator": data.get("about_creator", ""),
        "used_model": model_name 
    }

