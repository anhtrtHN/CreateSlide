import os
import json
from google import genai
from google.genai import types
import docx
import io

# Define the schema explicitly for clarity, though Gemini's response_mime_type="application/json"
# combined with system instructions is often enough. For stricter control, we could use
# schema constraints, but prompt instructions are usually sufficient for this use case.

SYSTEM_INSTRUCTION = """
Bạn là chuyên gia thiết kế bài thuyết trình. Hãy trích xuất nội dung từ tài liệu và trả về cấu trúc JSON chính xác cho bài thuyết trình gồm 8-10 slide.
JSON Schema bắt buộc:
{
  "title": "Tên bài thuyết trình",
  "slides": [
    {
      "title": "Tiêu đề Slide",
      "content": ["Ý chính 1", "Ý chính 2", "Ý chính 3"],
      "notes": "Ghi chú diễn giả"
    }
  ]
}
"""

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from a DOCX file bytes."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        raise ValueError(f"Lỗi khi đọc file DOCX: {str(e)}")

def analyze_document(file_bytes: bytes, mime_type: str, api_key: str = None) -> dict:
    """
    Sends document content to Gemini and returns parsed JSON.
    """
    # Use provided key or env var
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    
    if not key:
        raise ValueError("Thiếu Google API Key. Vui lòng thiết lập biến môi trường hoặc nhập vào giao diện.")

    try:
        client = genai.Client(api_key=key)
        
        parts = []
        prompt = "Hãy phân tích tài liệu này và tạo cấu trúc bài thuyết trình theo định dạng JSON đã yêu cầu."

        if mime_type == "application/pdf":
            # Multimodal for PDF
            parts.append(types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"))
            parts.append(types.Part.from_text(text=prompt))
        
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Text extraction for DOCX
            text_content = extract_text_from_docx(file_bytes)
            parts.append(types.Part.from_text(text=f"{prompt}\n\nNội dung tài liệu:\n{text_content}"))
        
        else:
            raise ValueError(f"Định dạng file không được hỗ trợ: {mime_type}")

        # List of models to try in order of preference (expanded for resilience)
        models_to_try = [
            "gemini-2.0-flash", 
            "gemini-2.5-flash", 
            "gemini-2.0-flash-lite", 
            "gemini-flash-latest", 
            "gemini-2.0-flash-exp"
        ]
        
        last_exception = None
        import time

        for model_name in models_to_try:
            try:
                print(f"Trying model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.7
                    )
                )
                # If successful, break the loop
                break
            except Exception as e:
                last_exception = e
                error_str = str(e)
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    print(f"Quota exceeded for {model_name}. Waiting 10s before trying next model...")
                    time.sleep(10)
                    continue
                elif "NOT_FOUND" in error_str or "404" in error_str:
                    print(f"Model {model_name} not found. Trying next...")
                    continue
                else:
                    # If it's another error, try next just in case
                    print(f"Error with {model_name}: {error_str}. Trying next...")
                    continue
        else:
            # If we exhausted the loop without success
            raise last_exception if last_exception else RuntimeError("All models failed.")

        # Parse JSON
        if not response.text:
            raise ValueError("Gemini không trả về nội dung.")
            
        cleaned_text = response.text.strip()
        # Strip markdown code blocks if present
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.strip("`")
            if cleaned_text.startswith("json"):
                cleaned_text = cleaned_text[4:]
            cleaned_text = cleaned_text.strip()
            
        return json.loads(cleaned_text)

    except Exception as e:
        # Catch network errors, API errors, or JSON parsing errors
        raise RuntimeError(f"Lỗi xử lý AI: {str(e)}")
