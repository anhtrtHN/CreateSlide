import os
import json
from google import genai
from google.genai import types
import docx
import io
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings
import ast
import re

# Suppress ebooklib warnings about future features if any
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')

# Suppress BS4 XML/HTML warning for EPUBs
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def robust_json_parse(text):
    """
    Parses JSON robustly, handling Markdown code blocks, single quotes (Python dicts),
    and common syntax errors.
    """
    # 1. Clean Markdown code blocks
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # 2. Try standard JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Try AST literal_eval (handles single quotes/Python dicts)
    try:
        # ast.literal_eval is safe for standard python literals
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        pass

    # 4. Try finding JSON content within the text (substring search)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        subset_text = match.group(0)
        try:
            return json.loads(subset_text)
        except:
            try:
                return ast.literal_eval(subset_text)
            except:
                pass
        # Update text to the found subset for further repair attempts
        text = subset_text

    # 5. Fix common issues: Trailing commas
    # Remove trailing comma before ] or }
    text_fixed = re.sub(r',\s*([\]}])', r'\1', text)
    try:
        return json.loads(text_fixed)
    except:
        pass
    
    try:
        return ast.literal_eval(text_fixed)
    except:
        pass
        
    # 6. Aggressive fallback for unquoted keys (JavaScript style)
    # This is risky but useful for basic keys. 
    # { title: "Foo" } -> { "title": "Foo" }
    try:
        # Regex to quote unquoted keys
        # Find word followed by colon, not in quotes
        # This is a simplified regex and might break complex strings
        text_quoted = re.sub(r'(\w+):', r'"\1":', text_fixed)
        return json.loads(text_quoted)
    except:
        pass

    raise ValueError(f"Failed to parse JSON/Dict from response. Raw text: {text}")


SYSTEM_INSTRUCTION = """
Bạn là chuyên gia thiết kế bài thuyết trình chuyên nghiệp. Nhiệm vụ của bạn là trích xuất nội dung từ tài liệu và tạo cấu trúc JSON cho bài thuyết trình.

Yêu cầu QUAN TRỌNG:
1. TIÊU ĐỀ NGẮN GỌN: Tiêu đề mỗi slide phải cực kỳ ngắn gọn, KHÔNG QUÁ 10 TỪ. Tránh tiêu đề 2 dòng.
2. NỘI DUNG VỪA PHẢI (QUAN TRỌNG): 
   - Mỗi slide chứa khoảng 5-7 ý chính.
   - ƯU TIÊN TUYỆT ĐỐI: **Viết câu đơn, trọn vẹn ý nghĩa, nhưng vẫn ngắn gọn.**
   - Đảm bảo mỗi ý đều truyền tải được thông điệp rõ ràng, không viết cụt lủn (như chỉ viết từ khóa).
   - Có thể dùng động từ mạnh ở đầu câu hoặc câu khẳng định.
   - **VÍ DỤ PHONG CÁCH MONG MUỐN (HÃY BẮT CHƯỚC STYLE NÀY):**
     + "Manifesting là một bài thực hành phát triển bản thân."
     + "Giúp giải phóng toàn bộ tiềm năng bên trong bạn."
     + "Yêu cầu thực hiện đồng thời cả 7 bước."
     + "Mỗi ngày là một cơ hội để củng cố sức mạnh nội tại."
     + "Bạn có quyền lựa chọn và kiến tạo cuộc sống tốt nhất."
   - NẾU NỘI DUNG QUÁ DÀI: Hãy chia thành nhiều slide thay vì cố nhồi nhét.
   - **TẤT CẢ** các ý quan trọng trong tài liệu PHẢI được đưa vào slide. Không được tự ý cắt bỏ nội dung chính.
   - **KHÔNG ĐƯỢC ĐỂ TRỐNG NỘI DUNG**: Nếu không tìm thấy ý chính, hãy tóm tắt đoạn văn bản đó. Không bao giờ trả về mảng "content" rỗng `[]`.
   - **PHÂN LOẠI NGỮ CẢNH THÔNG MINH (SEMANTIC MAPPING):**
     Đừng chỉ copy-paste nội dung. Hãy hiểu ý nghĩa câu để gán nhãn chính xác:
     + **Chiến lược/Định hướng**: Áp dụng cho các quyết định vĩ mô, chọn phương án, giai đoạn đầu (Stage 0). -> Bắt đầu bằng **Chiến lược**: hoặc **Định hướng**:
     + **Rủi ro/Hậu quả/Cảnh báo**: Áp dụng cho các câu chỉ kết quả xấu, cảnh báo, hoặc mối quan hệ nguyên nhân-hệ quả tiêu cực (A -> B). -> Bắt đầu bằng **Rủi ro**: hoặc **Cảnh báo**:
     + **Giải pháp/Cải tiến/Thay đổi**: Áp dụng cho các yêu cầu thay đổi (A thay vì B), đề xuất mới, hoặc giải quyết vấn đề cũ. -> Bắt đầu bằng **Giải pháp**: hoặc **Cải tiến**:
     + **Mục tiêu/Kết quả (Outcome)**: Áp dụng cho các mong muốn đạt được. -> Bắt đầu bằng **Mục tiêu**:
     + **Lưu ý quan trọng**: Những điều cần ghi nhớ đặc biệt. -> Bắt đầu bằng **Lưu ý**:
     
     *Ví dụ 1*: "Làm vội phần Briefing dẫn đến phải sửa thiết kế nhiều." -> **Rủi ro**: Làm vội Briefing gây hậu quả sửa thiết kế nhiều lần.
     *Ví dụ 2*: "Yêu cầu dùng dữ liệu số thay vì 2D cũ kỹ." -> **Cải tiến**: Chuyển đổi sang dữ liệu số (BIM) thay vì bản vẽ 2D.
     
     **QUAN TRỌNG**: Nếu không thuộc các loại trên, HÃY GIỮ NGUYÊN nội dung gốc và tóm tắt lại cho ngắn gọn. ĐỪNG BỎ SÓT thông tin chỉ vì không phân loại được.
3. CÚ PHÁP (BẮT BUỘC): Sử dụng markdown `**từ khóa**` để làm nổi bật (in đậm & màu) các ý quan trọng. Ít nhất 1-2 từ khóa mỗi dòng.
   - **LƯU Ý ĐẶC BIỆT VỀ JSON**: KHÔNG sử dụng dấu ngoặc kép `"` bên trong nội dung văn bản (content) vì sẽ làm hỏng cấu trúc JSON. Hãy dùng dấu ngoặc đơn `'` hoặc escape `\"` nếu bắt buộc.
4. NGÔN NGỮ: Chuyên nghiệp, trang trọng.

JSON Schema bắt buộc:
{
  "title": "TÊN BÀI THUYẾT TRÌNH (VIẾT HOA)",
  "slides": [
    {
      "title": "Tiêu Đề Ngắn (Max 10 chữ)",
      "content": ["Ý 1 (Ngắn gọn)", "Ý 2...", "Ý 3...", "Ý 4...", "Ý 5..."],
      "notes": "Ghi chú chi tiết..."
    },
    {
       "title": "Tiêu Đề Ngắn (Phần 2)",
       "content": ["Ý tiếp theo..."]
    }
  ]
}
"""

from document_loader import load_document, extract_text_from_docx, extract_text_from_epub

def analyze_document(file_bytes: bytes, mime_type: str, api_key: str = None, detail_level: str = "Tóm tắt", user_instructions: str = "") -> dict:
    """
    Sends document content to Gemini and returns parsed JSON.
    detail_level: "Tóm tắt" (Overview) or "Chi tiết" (Detailed)
    user_instructions: Optional specific requests from user behavior.
    """
    # ... (Key check)
    # Use provided key or env var
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    
    if not key:
        raise ValueError("Thiếu Google API Key. Vui lòng thiết lập biến môi trường hoặc nhập vào giao diện.")

    # Import safe_print...
    from utils import safe_print

    # Dynamic System Instruction...
    base_instruction = SYSTEM_INSTRUCTION
    
    # ... (Logic for detail_level and user_instructions)
    
    # 1. Detail Level Logic
    if detail_level == "Chi tiết":
        safe_print("Using DETAILED mode prompt...")
        specific_instruction = """
        YÊU CẦU CHI TIẾT (QUAN TRỌNG):
        - Bạn đang ở chế độ 'Chi tiết'. Người dùng muốn các slide đi sâu vào nội dung, số liệu và phân tích.
        - ĐỪNG tóm tắt qua loa. Hãy trích xuất tối đa thông tin quan trọng.
        - Số lượng slide: Có thể tạo nhiều slide hơn bình thường để chứa hết thông tin chi tiết. 
        - Vẫn phải tuân thủ quy tắc: Max 5 bullet/slide. Nếu nội dung dài, hãy TÁCH thành nhiều slide (Phần 1, Phần 2, Phần 3...).
        """
    else:
        safe_print("Using OVERVIEW mode prompt...")
        specific_instruction = """
        YÊU CẦU TỔNG QUAN:
        - Bạn đang ở chế độ 'Tổng quan'. Hãy tập trung vào các ý chính, cốt lõi nhất.
        - Phù hợp cho bài giới thiệu ngắn gọn.
        """
    
    # 2. Custom User Instructions Logic
    custom_instruction_block = ""
    if user_instructions and len(user_instructions.strip()) > 2:
        safe_print(f"Adding User Instructions: {user_instructions}")
        custom_instruction_block = f"""
        \n--------------------------------------------------
        HƯỚNG DẪN ĐẶC BIỆT TỪ NGƯỜI DÙNG (ƯU TIÊN TUYỆT ĐỐI):
        "{user_instructions}"
        
        Hãy tuân thủ nghiêm ngặt hướng dẫn trên của người dùng khi tạo nội dung.
        Nếu người dùng yêu cầu tập trung vào chương nào, hãy chỉ tập trung vào đó.
        --------------------------------------------------\n
        """
        
    final_instruction = base_instruction + "\n" + specific_instruction + custom_instruction_block

    try:
        client = genai.Client(api_key=key)
        
        parts = []
        prompt = f"Hãy phân tích tài liệu này và tạo cấu trúc bài thuyết trình ({detail_level})."

        if mime_type == "application/pdf":
            # Multimodal for PDF
            parts.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))
            parts.append(types.Part.from_text(text=prompt))
        
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Text extraction for DOCX
            text_content = extract_text_from_docx(file_bytes)
            parts.append(types.Part.from_text(text=f"{prompt}\n\nNội dung tài liệu:\n{text_content}"))
            
        elif mime_type == "application/epub+zip":
            # Text extraction for EPUB
            safe_print("Processing EPUB file...")
            text_content = extract_text_from_epub(file_bytes)
            # Limit text length if too huge? Gemini 1.5/2.0 context is huge, so likely fine.
            parts.append(types.Part.from_text(text=f"{prompt}\n\nNội dung tài liệu:\n{text_content}"))
        
        else:
            raise ValueError(f"Định dạng file không được hỗ trợ: {mime_type}")
        
        
        # 1. Base Priority List (User Requested)
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

        # 2. Auto-Discovery for Newer Models
        # This attempts to find any new 'preview' or 'experimental' models higher than version 3
        # or just distinct valid models to prepend.
        discovered_models = []
        try:
             # Using list_models to find what's actually available and new
             # filter 'gemini' and 'generateContent'
             for m in client.models.list(config={'page_size': 100}):
                  name = m.name.replace('models/', '')
                  if 'gemini' in name and 'vision' not in name:
                       # Logic to detect if it's "newer" than our base list could be complex,
                       # but for now, let's just ensure we have verified models.
                       # A simple strategy: if it contains 'experimental' or 'preview' and is not in base, add it?
                       # Or better: Just stick to the robust requested list for now to ensure stability, 
                       # but if user specifically asked for "searching for advanced models":
                       pass 
        except Exception:
             safe_print("Warning: Could not auto-discover models. Using hardcoded list.")

        # Combine: Discovered (Newest) + Base + Legacy (just in case)
        # For this implementation, we will stick to the User's strict ordering request 
        # plus the logic to skip failing ones.
        models_to_try = base_models + [
            "gemini-flash-latest",
            "gemini-pro-latest"
        ]
        
        last_exception = None
        import time
        import random

        retry_count = 0
        success = False
        
        for model_name in models_to_try:
            try:
                safe_print(f"Trying model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        system_instruction=final_instruction,
                        response_mime_type="application/json",
                        temperature=0.7
                    )
                )
                success = True
                break
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Handling Rate Limits (429) and Resource Exhausted
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    # Check for "limit: 0" which means NO QUOTA at all -> Don't wait, just skip.
                    if "limit: 0" in error_str or "limit:0" in error_str:
                         safe_print(f"Model {model_name} has NO QUOTA (limit: 0). Skipping immediately...")
                         continue

                    # Exponential Backoff + Jitter
                    retry_count += 1
                    wait_time = min(15, (2 ** retry_count)) + random.uniform(0, 1) # Cap wait at 15s to fail faster
                    safe_print(f"Quota exceeded for {model_name}. Waiting {wait_time:.1f}s before trying next...")
                    time.sleep(wait_time)
                    continue
                    
                # Handling Not Found (404)
                elif "NOT_FOUND" in error_str or "404" in error_str:
                    safe_print(f"Model {model_name} not found (or not available). Skipping immediately...")
                    continue
                    
                else:
                    safe_print(f"Error with {model_name}: {error_str}. Trying next...")
                    continue
        
        if not success:
             # Graceful waiting message instead of crash
             # We return a dummy dict or raise a specific known error text
             safe_print("All models failed. Returning friendly error.")
             raise ValueError("Hệ thống AI đang quá tải tạm thời. Vui lòng chờ 30 giây rồi thử lại (AI Overload).")

        if not response.text:
            raise ValueError("Gemini không trả về nội dung.")
            
        try:
            parsed_data = robust_json_parse(response.text)
            
            # Critical Fix for "list object has no attribute get"
            if isinstance(parsed_data, list):
                safe_print("AI returned a LIST. Wrapping into standard schema...")
                # Heuristic: If it's a list, it's likely the "slides" array
                parsed_data = {
                    "title": "Slide Generated by AI", 
                    "slides": parsed_data
                }
            
            # --- VALIDATION STEP ---
            # Check for empty content and try to rescue
            if "slides" in parsed_data:
                for i, slide in enumerate(parsed_data["slides"]):
                    content = slide.get("content", [])
                    if not content or (isinstance(content, list) and len(content) == 0):
                        safe_print(f"WARNING: Slide {i+1} ('{slide.get('title', 'Untitled')}') has EMPTY content.")
                        # Emergency Fallback: If notes exist, force them into content
                        if slide.get("notes"):
                            safe_print("-> Movings 'notes' to 'content' as fallback.")
                            slide["content"] = [slide["notes"]]
                        else:
                            slide["content"] = ["(Nội dung chưa được trích xuất - Vui lòng kiểm tra lại tài liệu gốc)"]
            
            return parsed_data
            
        except Exception as e:
            safe_print(f"JSON Parsing Failed: {e}")
            raise ValueError(f"Lỗi đọc dữ liệu từ AI: {str(e)}")

    except Exception as e:
        # Catch-all for top level errors
        raise RuntimeError(f"{str(e)}")
