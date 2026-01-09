import io
from typing import Dict, Any
from pptx import Presentation
from pptx.util import Pt, Cm
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
import re

def create_pptx(json_data: Dict[str, Any], template_pptx_bytes: bytes | None = None) -> io.BytesIO:
    """
    Generates a PowerPoint presentation from JSON data.
    Returns: BytesIO object of the .pptx file.
    """
    if template_pptx_bytes:
        prs = Presentation(io.BytesIO(template_pptx_bytes))
        # Clear existing slides from the template explicitly and safely
        # We need to remove the relationship (rId) to avoid corruption
        xml_slides = prs.slides._sldIdLst
        slides = list(xml_slides)
        
        for s in slides:
             rId = s.rId
             prs.part.drop_rel(rId) # Critical: Remove the relationship
             xml_slides.remove(s)   # Remove the slide entry
            
        print(f"Template loaded and cleared. Remaining slides: {len(prs.slides)}")
        
    else:
        prs = Presentation() # Uses default template

    # Helper to find usable layouts
    def get_layout(prs, preferred_index, needs_body=False):
        # Try preferred index first
        if preferred_index < len(prs.slide_layouts):
            layout = prs.slide_layouts[preferred_index]
            if not needs_body:
                return layout
            # Check if it has a body placeholder (usually idx 1)
            if len(layout.placeholders) > 1:
                return layout
        
        # Fallback: Search for a suitable layout
        for layout in prs.slide_layouts:
            if needs_body and len(layout.placeholders) > 1:
                return layout
        
        # Last resort: just return first layout
        return prs.slide_layouts[0]

    # 1. Main Title Slide
    # layout 0 usually title
    title_layout = get_layout(prs, 0) 
    slide = prs.slides.add_slide(title_layout)
    
    if slide.shapes.title:
        title_text = json_data.get("title", "Bài thuyết trình AI")
        slide.shapes.title.text = title_text.upper()
    
    # Safely set subtitle if placeholder exists
    if len(slide.placeholders) > 1:
        try:
            slide.placeholders[1].text = "Được tạo bởi SlideGenius"
        except (IndexError, KeyError):
            pass # Skip if no placeholder accessible

    # 2. Content Slides
    slides_content = json_data.get("slides", [])
    
    # Try to find a content layout (often index 1, needs body)
    content_layout = get_layout(prs, 1, needs_body=True)
    
    # ... existing code ...

    for slide_data in slides_content:
        slide = prs.slides.add_slide(content_layout)
        
        # Set Title and Clean "Slide X:" prefix
        if slide.shapes.title:
            raw_title = slide_data.get("title", "")
            # Remove "Slide 1:", "Slide 01", etc.
            clean_title = re.sub(r'^Slide\s+\d+[:.]?\s*', '', raw_title, flags=re.IGNORECASE)
            slide.shapes.title.text = clean_title
            
            # --- Layout Refinement: Strict Title Geometry ---
            # Heuristic for Title Height (1 vs 2 lines)
            # Assumption: 36pt font, ~25 chars per line is safe estimate for width?
            # Slide width ~33.8cm (16:9). Width - 2cm margins = ~31.8cm.
            # 36pt ~ 1.27cm height? Char width avg ~0.6cm?
            # 31.8cm / 0.6 = ~50 chars per line.
            # Let's say breakpoint is 45 chars.
            
            title_text_len = len(clean_title)
            is_multiline_title = title_text_len > 45
            
            # Dynamic Height & Gap
            title_height = Cm(3.5) if is_multiline_title else Cm(2.0)
            
            slide.shapes.title.top = Cm(0.5)
            slide.shapes.title.left = Cm(1.0)
            slide.shapes.title.width = prs.slide_width - Cm(2.0)
            slide.shapes.title.height = title_height
            
            # Title Font Styling (Request: 36pt, Top Align)
            if slide.shapes.title.text_frame:
                tf_title = slide.shapes.title.text_frame
                tf_title.word_wrap = True 
                tf_title.auto_size = MSO_AUTO_SIZE.NONE
                # Key Fix: Vertical Alignment TOP
                tf_title.vertical_anchor = MSO_ANCHOR.TOP
                
                if tf_title.paragraphs:
                    p = tf_title.paragraphs[0]
                    p.font.size = Pt(36)
                    p.font.bold = True
                    p.alignment = PP_ALIGN.LEFT # Usually titles are left or center. Left looks pro.
                    
                    if not is_multiline_title:
                         # Extra hint: if absolute top is needed, check margins.
                         tf_title.margin_top = 0
                         
        # Set Content (Body)
        # Find the first non-title placeholder
        body_shape = None
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1: # Standard body
                body_shape = shape
                break
        
        # Fallback to any second placeholder if idx 1 not found
        if not body_shape and len(slide.placeholders) > 1:
             body_shape = slide.placeholders[1]

        if body_shape and hasattr(body_shape, "text_frame"):
            # --- Layout Refinement: Adjust Margins & Top ---
            
            margin_side = Cm(1.5)
            # Body Top = Title Top (0.5) + Title Height + Small Gap (0.2)
            # Dynamic Calculation
            title_bottom = Cm(0.5) + title_height
            gap = Cm(0.2) 
            margin_top = title_bottom + gap
            
            margin_bottom = Cm(1.0)
            
            body_shape.left = margin_side
            body_shape.top = margin_top
            body_shape.width = prs.slide_width - (margin_side * 2)
            body_shape.height = prs.slide_height - margin_top - margin_bottom
            
            tf = body_shape.text_frame
            tf.word_wrap = True
            
            # --- Hybrid Strategy: Manual Calc + Native Auto-Fit ---
            # 1. We calculate a safe "base" font size manually so the slide looks good immediately on open.
            # 2. We set TEXT_TO_FIT_SHAPE so PowerPoint handles future edits/overflows gracefully.
            
            # Constants for Heuristic
            MAX_FONT_SIZE = 24
            MIN_FONT_SIZE = 10
            
            # Estimate Capacity:
            # Box dimensions: ~22cm wide x ~8cm high.
            # At 24pt, line height ~30pt. Height 8cm=226pt -> ~7 lines.
            # Width 22cm=623pt. Avg char width ~11pt -> ~56 chars/line.
            # Total Chars @ 24pt = 7 * 56 = ~392 chars.
            # Let's be conservative: 350 chars for 24pt.
            # UPDATED: User reported overflow. Drastically reducing logical capacity for safer scaling.
            BASE_CAPACITY_AT_24PT = 300 
            
            total_text_len = sum(len(str(c)) for c in slide_data.get("content", []))
            
            if total_text_len <= BASE_CAPACITY_AT_24PT:
                font_size_pt = MAX_FONT_SIZE
            else:
                # Scaling formula
                import math
                ratio = BASE_CAPACITY_AT_24PT / total_text_len
                scale_factor = math.sqrt(ratio)
                font_size_pt = max(min(MAX_FONT_SIZE * scale_factor, MAX_FONT_SIZE), MIN_FONT_SIZE)
            
            # Apply calculated font size AND set AutoFit
            tf.word_wrap = True
            tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE # Re-enable Native Auto-Fit
            
            # Clear default paragraph
            tf.clear()
            
            content = slide_data.get("content", [])
            for i, item in enumerate(content):
                # Reuse the first paragraph if it exists
                if i == 0 and len(tf.paragraphs) == 1:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                p.level = 0
                
                # Parse markdown
                parts = re.split(r'(\*\*.*?\*\*)', str(item))
                
                for part in parts:
                    if not part: continue
                    
                    run = p.add_run()
                    # Check for bold marker
                    if part.startswith('**') and part.endswith('**'):
                        text_content = part[2:-2] # Strip **
                        run.text = text_content
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0, 112, 192) # Emphasis Blue
                    else:
                        run.text = part
                        
                    run.font.size = Pt(font_size_pt) # Set the safe start size
                
                # Adjust spacing based on size
                # Smaller text needs less spacing
                spacing = max(3, font_size_pt * 0.3)
                p.space_before = Pt(spacing)
                p.space_after = Pt(spacing)
        
        # Set Speaker Notes
        
        # Set Speaker Notes
        notes = slide_data.get("notes", "")
        if notes:
            if slide.has_notes_slide:
                notes_slide = slide.notes_slide
                notes_slide.notes_text_frame.text = notes

    # Save to BytesIO
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output
