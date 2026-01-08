import io
from typing import Dict, Any
from pptx import Presentation
from pptx.util import Pt

def create_pptx(json_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a PowerPoint presentation from JSON data.
    Returns: BytesIO object of the .pptx file.
    """
    prs = Presentation() # Uses default template

    # Layout indices for default template:
    # 0: Title Slide (Title + Subtitle)
    # 1: Title and Content (Title + Bullet points)
    
    TITLE_SLIDE_LAYOUT = 0
    CONTENT_SLIDE_LAYOUT = 1

    # 1. Main Title Slide
    slide_layout = prs.slide_layouts[TITLE_SLIDE_LAYOUT]
    slide = prs.slides.add_slide(slide_layout)
    
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = json_data.get("title", "Bài thuyết trình AI")
    subtitle.text = "Được tạo bởi SlideGenius"

    # 2. Content Slides
    slides_content = json_data.get("slides", [])
    
    for slide_data in slides_content:
        slide_layout = prs.slide_layouts[CONTENT_SLIDE_LAYOUT]
        slide = prs.slides.add_slide(slide_layout)
        
        # Set Title
        if slide.shapes.title:
            slide.shapes.title.text = slide_data.get("title", "")
        
        # Set Content (Body)
        if len(slide.placeholders) > 1:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.word_wrap = True
            
            content = slide_data.get("content", [])
            if isinstance(content, str):
                content = [content]
            
            # Clear default paragraph
            tf.clear()
            
            for item in content:
                p = tf.add_paragraph()
                p.text = item
                p.level = 0
                # Optional: Adjust font if needed
                # p.font.size = Pt(18)

        # Set Speaker Notes
        notes = slide_data.get("notes", "")
        if notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = notes

    # Save to BytesIO
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output
