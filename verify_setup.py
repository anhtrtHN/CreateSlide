import sys
import os
import base64
import json
from unittest.mock import MagicMock

# Add current dir to path
sys.path.append(os.getcwd())

try:
    print("Testing imports...")
    import mesop
    import google.genai
    import docx
    import pptx
    from slide_engine import create_pptx
    print("Imports successful.")

    print("Testing PPTX generation logic...")
    mock_data = {
        "title": "Test Presentation",
        "slides": [
            {
                "title": "Slide 1",
                "content": ["Point 1", "Point 2"],
                "notes": "Speaker notes here"
            },
            {
                "title": "Slide 2",
                "content": "Single point string",
            }
        ]
    }
    
    pptx_io = create_pptx(mock_data)
    pptx_bytes = pptx_io.read()
    if len(pptx_bytes) > 0:
        print(f"PPTX generated successfully. Size: {len(pptx_bytes)} bytes")
    else:
        print("PPTX generation failed (empty output).")
        sys.exit(1)

    print("Verification passed!")

except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Runtime Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
