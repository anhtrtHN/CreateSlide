
import os
import io
import docx
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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

def extract_text_from_epub(file_bytes: bytes) -> str:
    """Extracts text from an EPUB file bytes."""
    try:
        # EbookLib requires a file path or a file-like object.
        # However, epub.read_epub usually takes a path. 
        # We save to a temp file or try to pass BytesIO if supported (often not fully).
        # Workaround: Write bytes to a temporary file.
        import tempfile
        
        tmp_path = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        book = epub.read_epub(tmp_path)
        full_text = []

        # Import safe_print locally since it's not at top level (avoid circular import if utils uses this)
        # But here we can just skip logging or use standard print if needed, 
        # or better: return pure text and let caller log.
        
        items = list(book.get_items())
        
        for item in items:
            # Check for document type OR generic HTML/XHTML content
            # Some EPUBs mark chapters as ITEM_UNKNOWN or just don't set types correctly
            is_doc = item.get_type() == ebooklib.ITEM_DOCUMENT
            is_html = item.media_type and ('html' in item.media_type or 'xml' in item.media_type)
            
            if is_doc or is_html:
                content = item.get_content()
                if not content:
                    continue
                                    
                # Use BS4 to strip HTML tags
                soup = BeautifulSoup(content, 'html.parser')
                
                # Use separator to prevent word mashing
                text = soup.get_text(separator=' ', strip=True)
                
                # Only add meaningful chunks
                if len(text) > 50:
                    full_text.append(text)
                
        # Clean up temp file
        try:
            os.remove(tmp_path)
        except:
            pass
            
        result = '\n\n'.join(full_text)
        return result

    except Exception as e:
        raise ValueError(f"Lỗi khi đọc file EPUB: {str(e)}")

def load_document(file_bytes: bytes, mime_type: str) -> str:
    """
    Loads document content based on mime type.
    Returns: Text content of the document.
    """
    if mime_type == "application/pdf":
        raise NotImplementedError("PDF loading is handled by Gemini Multimodal, not text extraction yet.")
    
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file_bytes)
        
    elif mime_type == "application/epub+zip":
        return extract_text_from_epub(file_bytes)
    
    else:
        raise ValueError(f"Định dạng file không được hỗ trợ để trích xuất text thuần: {mime_type}")
