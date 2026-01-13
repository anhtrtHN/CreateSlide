
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

# New Prompts for Deep Dive
PROMPT_1_STRUCTURE = """I have uploaded a document. I need to create a comprehensive, deep-dive summary of this book. First, please analyze the entire document and provide a detailed table of contents, including all chapters and major sub-sections. For each chapter, provide a brief 2-sentence description of its primary objective. After providing this outline, wait for my instruction to start the detailed summarization. Note: Please output in Vietnamese."""

PROMPT_2_DETAILS = """Now, please provide a highly detailed summary for ALL CHAPTERS.
Requirements:
Length: Detailed and comprehensive.
Content: Do not just list bullet points. Elaborate on the author’s arguments, include specific case studies, examples, and data mentioned in the text.
Format: Use clear headings, sub-headings, and bold key concepts. Use nested bullet points for complex explanations.
Tone: Maintain a professional and analytical tone, capturing the nuance of the author's original message.
Language: Vietnamese.
"""

PROMPT_3_SYNTHESIS = """Based on the entire document, please provide a comprehensive synthesis section (approx. 3 pages) that covers:
Core Framework: A detailed breakdown of the central methodology or philosophy proposed by the author.
Critical Analysis: Strengths and potential weaknesses of the author's arguments.
Actionable Insights: A list of 10 high-impact takeaways that can be applied in real-world scenarios.
Glossary: Define the key technical terms or unique vocabulary used throughout the book.
Language: Vietnamese.
"""

PROMPT_4_FINAL = """Please review the previous summaries and provide a 'Final Executive Overview' (approx. 1,000 words) that connects all the themes discussed. Ensure this overview serves as a high-level bridge for a reader who needs to understand the overarching narrative of the book without losing the technical depth.
Language: Vietnamese.
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
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-3-flash-preview",
        "gemini-flash-latest"
    ]

    chat = None
    used_model = None

    for model_name in models_to_try:
        try:
            print(f"Initializing Chat with model: {model_name}...")
            chat = client.chats.create(model=model_name)
            # Test a quick ping or just proceed. The first sendMessage will reveal if it works.
            # But we can't easily 'switch' mid-conversation if step 2 fails. 
            # So we just pick one that starts successfully.
            # Applying a start-up check might be good, but expensive.
            # Let's just proceed with the first one that works for the first step, 
            # and if it fails mid-way, well, deep dive is hard to resume.
            # We will rely on the retry logic for the chosen model.
            used_model = model_name
            break
        except Exception as e:
            print(f"Model {model_name} failed to init: {e}")
            continue
    
    if not chat:
        raise ValueError("Could not initialize chat with any model.")
    
    print(f"Using model: {used_model}")

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

    # Initial Prompt (Prompt 1)
    parts.append(types.Part.from_text(text=PROMPT_1_STRUCTURE))
    
    def send_message_with_retry(content, retries=10, initial_delay=2):
        for attempt in range(retries):
            try:
                # print(f"Sending message (Attempt {attempt+1})...")
                return chat.send_message(content)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    delay = initial_delay * (1.5 ** attempt) # Slower backoff
                    print(f"Rate limit hit. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    raise e
        raise ValueError("Exceeded maximum retries due to rate limits.")

    # Step 1: Structure
    print("Step 1/4: Analyzing Structure...")
    resp1 = send_message_with_retry(parts)
    structure_text = resp1.text

    # Step 2: Deep Dive Details
    print("Step 2/4: Generating Detailed Content...")
    resp2 = send_message_with_retry(PROMPT_2_DETAILS)
    details_text = resp2.text

    # Step 3: Synthesis
    print("Step 3/4: Synthesizing...")
    resp3 = send_message_with_retry(PROMPT_3_SYNTHESIS)
    synthesis_text = resp3.text

    # Step 4: Final Overview
    print("Step 4/4: Finalizing Executive Overview...")
    resp4 = send_message_with_retry(PROMPT_4_FINAL)
    final_text = resp4.text
    
    print("Deep Dive Completed.")
    return {
        "mode": "deep_dive",
        "structure": structure_text,
        "details": details_text,
        "synthesis": synthesis_text,
        "executive_overview": final_text
    }

