import os
# Patch IO immediately to prevent Windows console crashes
# Patch IO immediately to prevent Windows console crashes
from utils import suppress_console_output
# suppress_console_output()

import base64
import mesop as me
import mesop.labs as mel
from dataclasses import field
from dotenv import load_dotenv
from ai_engine import analyze_document
from slide_engine import create_pptx
from summarizer import summarize_document, save_summary_to_pdf, summarize_book_deep_dive


load_dotenv()

@me.stateclass
class State:
    # Processing State
    processing_status: str = "idle" # idle, analyzing, generating, done, error
    logs: list[str] = field(default_factory=list)
    error_message: str = ""
    
    # Input Data
    uploaded_file_bytes: bytes = b""
    uploaded_mime_type: str = ""
    uploaded_filename: str = ""
    user_topic: str = ""
    
    # Template Data
    template_file_bytes: bytes = b""
    template_filename: str = ""
    
    # Output Data
    pptx_filename: str = ""
    pptx_content_base64: str = ""
    
    # Summary Data
    pdf_filename: str = ""
    pdf_content_base64: str = ""
    
    # Detail Configuration
    is_detailed: bool = False
    
    # Custom Instructions
    user_instructions: str = ""

def on_load(e: me.LoadEvent):
    me.set_theme_mode("system")

def handle_upload(event: me.UploadEvent):
    state = me.state(State)
    file = event.file
    
    # Store file in state
    state.uploaded_file_bytes = file.read()
    state.uploaded_mime_type = file.mime_type
    state.uploaded_filename = file.name
    
    # reset logs/status
    state.logs = [f"Đã tải lên: {file.name}", "System: Console Output Suppressed (v3)"]
    state.processing_status = "ready"
    state.error_message = ""

def handle_topic_input(e: me.InputEvent):
    state = me.state(State)
    state.user_topic = e.value

def handle_template_upload(event: me.UploadEvent):
    state = me.state(State)
    file = event.file
    
    # Store template in state
    state.template_file_bytes = file.read()
    state.template_filename = file.name
    
    state.logs.append(f"Đã tải lên mẫu: {file.name}")

def on_detail_change(e: me.CheckboxChangeEvent):
    state = me.state(State)
    state.is_detailed = e.checked

def handle_user_instruction(e: me.InputEvent):
    state = me.state(State)
    state.user_instructions = e.value



def generate_summary(e: me.ClickEvent):
    state = me.state(State)
    
    if not state.uploaded_file_bytes:
        state.error_message = "Vui lòng tải lên file tài liệu trước."
        return

    state.processing_status = "analyzing_summary"
    state.error_message = ""
    
    state.logs.append(f"Source Document: {state.uploaded_filename}")
    state.logs.append("Đang tóm tắt tài liệu với Gemini...")
    yield # Yield to update UI
    
    try:
        # 1. Summarize
        api_key_env = os.environ.get("GOOGLE_API_KEY")
        
        if state.is_detailed:
            state.logs.append("Đang chạy chế độ Deep Dive (4 bước)... Quá trình này có thể mất vài phút.")
            yield # Update UI
            summary_data = summarize_book_deep_dive(
                state.uploaded_file_bytes,
                state.uploaded_mime_type,
                api_key=api_key_env
            )
        else:
            summary_data = summarize_document(
                state.uploaded_file_bytes, 
                state.uploaded_mime_type, 
                api_key=api_key_env,
                user_instructions=state.user_instructions
            )
        
        state.logs.append("Tóm tắt hoàn tất. Đang tạo file PDF...")
        state.processing_status = "generating_pdf"
        yield
        
        # 2. Generate PDF
        # Use a temporary filename
        import tempfile
        original_name = state.uploaded_filename
        name_no_ext = original_name.rsplit('.', 1)[0]
        pdf_out_name = f"{name_no_ext}_summary.pdf"
        
        # We need a temp path for reportlab to write to
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            
        final_path = save_summary_to_pdf(summary_data, tmp_path)
        
        with open(final_path, "rb") as f:
            pdf_bytes = f.read()
            
        state.pdf_content_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        state.pdf_filename = pdf_out_name
        
        # Cleanup
        try:
             os.remove(final_path)
        except:
             pass

        state.logs.append(f"Đã tạo xong file: {state.pdf_filename}")
        state.processing_status = "summary_done"
        yield

    except Exception as ex:
        state.processing_status = "error"
        state.error_message = str(ex)
        state.logs.append(f"Lỗi: {str(ex)}")
        yield


def generate_slides(e: me.ClickEvent):
    state = me.state(State)
    
    if not state.uploaded_file_bytes:
        state.error_message = "Vui lòng tải lên file tài liệu trước."
        return

    state.processing_status = "analyzing"
    state.error_message = ""
    
    state.logs.append(f"Source Document: {state.uploaded_filename}")
    if state.template_filename:
        state.logs.append(f"Using Template: {state.template_filename}")
        if state.template_filename == state.uploaded_filename:
             state.logs.append("Warning: Source and Template are the same file!")

    state.logs.append("Đang phân tích tài liệu với Gemini...")
    yield # Yield to update UI
    
    try:
        # 1. Analyze
        # Note: We could pass user_topic to analyze_document if we update that signature, 
        # but for now we'll stick to the core requirement. 
        # Ideally, we append the topic to the prompt inside analyze_document if needed.
        # For this step, I will assume analyze_document is as defined, 
        # potentially updating it to accept extra context would be a good refinement later.
        
        detail_mode = "Chi tiết" if state.is_detailed else "Tóm tắt"
        state.logs.append(f"Chế độ phân tích: {detail_mode}")
        
        if state.user_instructions:
            state.logs.append(f"Hướng dẫn người dùng: {state.user_instructions[:50]}...")

        # Explicitly pass API Key to avoid env var scope issues in sub-modules
        api_key_env = os.environ.get("GOOGLE_API_KEY")
        
        slide_json = analyze_document(
            state.uploaded_file_bytes, 
            state.uploaded_mime_type, 
            api_key=api_key_env,
            detail_level=detail_mode,
            user_instructions=state.user_instructions
        )
        state.logs.append("Phân tích hoàn tất. Đang tạo cấu trúc slide...")
        state.processing_status = "generating"
        yield
        
        # 2. Generate PPTX
        pptx_io = create_pptx(slide_json, template_pptx_bytes=state.template_file_bytes if state.template_file_bytes else None)
        pptx_bytes = pptx_io.read()
        
        # Prepare filename
        original_name = state.uploaded_filename
        name_no_ext = original_name.rsplit('.', 1)[0]
        state.pptx_filename = f"{name_no_ext}_presentation.pptx"
        
        state.pptx_content_base64 = base64.b64encode(pptx_bytes).decode('utf-8')
        state.logs.append(f"Đã tạo xong file: {state.pptx_filename}")
        state.processing_status = "done"
        yield

    except Exception as ex:
        state.processing_status = "error"
        state.error_message = str(ex)
        state.logs.append(f"Lỗi: {str(ex)}")

        yield



def set_topic(e: me.ClickEvent):
    state = me.state(State)
    state.user_topic = e.key

@me.page(
    path="/",
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
    ],
    security_policy=me.SecurityPolicy(
        allowed_script_srcs=["https://fonts.googleapis.com", "https://fonts.gstatic.com"],
        allowed_connect_srcs=["https://fonts.googleapis.com", "https://fonts.gstatic.com"],
    ),
    on_load=on_load,
)
def main_page():
    state = me.state(State)

    with me.box(
        style=me.Style(
            background="#f8fafc",
            height="100vh",
            display="flex",
            flex_direction="column",
            font_family="Inter, sans-serif",
            padding=me.Padding.all(0),
        )
    ):
        # Header
        with me.box(
            style=me.Style(
                background="#ffffff",
                padding=me.Padding.symmetric(vertical=20, horizontal=32),
                border=me.Border(bottom=me.BorderSide(width=1, color="#e2e8f0")),
                display="flex",
                justify_content="space-between",
                align_items="center",
            )
        ):
            me.text(
                "SlideGenius",
                style=me.Style(
                    font_size=24,
                    font_weight=700,
                    color="#0f172a",
                ),
            )
            me.text("AI Powered Presentation Generator", style=me.Style(color="#64748b", font_size=14))

        # Main Layout: 2 Columns
        with me.box(
            style=me.Style(
                display="grid",
                grid_template_columns="1fr 1fr",
                gap=32,
                padding=me.Padding.all(32),
                height="calc(100vh - 80px)", # Adjust for header
                box_sizing="border-box",
            )
        ):
            # --- Left Column: Input ---
            with me.box(
                style=me.Style(
                    background="#ffffff",
                    padding=me.Padding.all(24),
                    border_radius=16,
                    box_shadow="0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    display="flex",
                    flex_direction="column",
                    gap=24,
                )
            ):
                me.text("Input Documents", style=me.Style(font_size=18, font_weight=600, color="#1e293b"))
                
                # File Uploader
                with me.box(style=me.Style(width="100%")):
                     me.text("Upload Document (PDF/DOCX/EPUB)", style=me.Style(font_size=14, color="#475569", margin=me.Margin(bottom=8)))
                     me.uploader(
                        label="Choose File",
                        accepted_file_types=["application/pdf", ".docx", ".epub"],
                        on_upload=handle_upload,
                        type="flat",
                        style=me.Style(
                            font_weight="500",
                        )
                    )
                
                if state.uploaded_filename:
                     with me.box(style=me.Style(background="#f0f9ff", padding=me.Padding.all(12), border_radius=8, display="flex", align_items="center", gap=8)):
                         me.icon("description", style=me.Style(color="#0284c7"))
                         me.text(state.uploaded_filename, style=me.Style(font_size=14, color="#0c4a6e"))

                # Template Uploader (Optional)
                with me.box(style=me.Style(width="100%")):
                     me.text("Slide Template (Optional .pptx)", style=me.Style(font_size=14, color="#475569", margin=me.Margin(bottom=8)))
                     me.uploader(
                        label="Upload Template",
                        accepted_file_types=[".pptx"],
                        on_upload=handle_template_upload,
                        type="stroked",
                        style=me.Style(
                            font_weight="500",
                        )
                    )
                
                if state.template_filename:
                     with me.box(style=me.Style(background="#faf5ff", padding=me.Padding.all(12), border_radius=8, display="flex", align_items="center", gap=8)):
                         me.icon("slideshow", style=me.Style(color="#9333ea"))
                         me.text(state.template_filename, style=me.Style(font_size=14, color="#6b21a8"))

                # Topic Input
                with me.box(style=me.Style(width="100%")):
                    me.input(
                        label="Chủ đề mong muốn (Tùy chọn)",
                        on_blur=handle_topic_input,
                        style=me.Style(width="100%"),
                        value=state.user_topic
                    )
                    
                    # Topic Suggestions
                    me.text("Gợi ý chủ đề phổ biến:", style=me.Style(font_size=12, color="#94a3b8", margin=me.Margin(top=12, bottom=8), font_weight=500))
                    
                    suggestions = [
                        "Kế hoạch kinh doanh", 
                        "Báo cáo thị trường", 
                        "Giáo án điện tử", 
                        "Hồ sơ năng lực", 
                        "Startup Pitch",
                        "Phân tích tài chính"
                    ]
                    
                    with me.box(style=me.Style(display="flex", flex_wrap="wrap", gap=8)):
                        for topic in suggestions:
                            is_selected = state.user_topic == topic
                            me.button(
                                topic,
                                key=topic,
                                on_click=set_topic,
                                type="stroked" if not is_selected else "flat",
                                color="primary" if is_selected else "warn", 
                                style=me.Style(
                                    font_size=12,
                                    border_radius=20, 
                                    # Custom override for unselected state to look cleaner
                                    color="#2563eb" if is_selected else "#64748b",
                                    border=me.Border.all(me.BorderSide(width=1, color="#2563eb" if is_selected else "#cbd5e1")),
                                    background="#eff6ff" if is_selected else "#ffffff",
                                    padding=me.Padding.symmetric(vertical=4, horizontal=12) 
                                )
                            )

                # Custom User Instructions
                with me.box(style=me.Style(width="100%", margin=me.Margin(top=24))):
                     me.textarea(
                        label="Hướng dẫn đặc biệt cho AI (Tùy chọn)",
                        placeholder="Ví dụ: Chỉ tập trung vào chương 2, giải thích kỹ thuật ngữ...",
                        on_blur=handle_user_instruction,
                        value=state.user_instructions,
                        rows=3,
                        style=me.Style(width="100%")
                    )

                # Detail Level Selection
                with me.box(style=me.Style(width="100%", margin=me.Margin(top=24))):
                    me.checkbox(
                        label="Chế độ Chi tiết (Deep Dive)",
                        checked=state.is_detailed,
                        on_change=on_detail_change,
                        style=me.Style(
                             # margin=me.Margin(bottom=16)
                        )
                    )
                    me.text(
                        "Nếu chọn: Tạo nhiều slide hơn, nội dung sâu hơn. Mặc định: Tổng quan ngắn gọn.", 
                        style=me.Style(font_size=12, color="#64748b", margin=me.Margin(top=4, left=32))
                    )

                # Generate Button
                is_loading = state.processing_status in ["analyzing", "generating"]
                # Button Logic
                is_disabled = is_loading or not state.uploaded_filename
                btn_bg = "#e2e8f0" if is_disabled else "#2563eb"
                btn_color = "#94a3b8" if is_disabled else "#000000"

                with me.box(
                    on_click=generate_slides if not is_disabled else None,
                    style=me.Style(
                        width="100%",
                        padding=me.Padding.symmetric(vertical=16),
                        margin=me.Margin(top=32),
                        background=btn_bg,
                        border_radius=8, # Make it look like a button
                        cursor="not-allowed" if is_disabled else "pointer",
                        display="flex",
                        justify_content="center",
                        align_items="center",
                        box_shadow="0 2px 4px rgba(0,0,0,0.1)" if not is_disabled else "none",
                    )
                ):
                    me.text(
                        "Generate Slides",
                        style=me.Style(
                            color=btn_color,
                            font_size=16,
                            font_weight="bold",
                            text_align="center",
                            z_index=10, # Force text to top
                        )
                    )
                
                # Summary Button Logic
                su_bg = "transparent"
                su_border = "#ea580c" if not is_disabled else "#fed7aa"
                su_color = "#ea580c" if not is_disabled else "#fed7aa"
                
                with me.box(
                    on_click=generate_summary if not is_disabled else None,
                    style=me.Style(
                        width="100%",
                        padding=me.Padding.symmetric(vertical=16),
                        margin=me.Margin(top=16),
                        background=su_bg,
                        border=me.Border.all(me.BorderSide(width=1, color=su_border)),
                        border_radius=8,
                        cursor="not-allowed" if is_disabled else "pointer",
                        display="flex",
                        justify_content="center",
                        align_items="center",
                    )
                ):
                   me.text(
                        "Generate Summary (PDF)",
                        style=me.Style(
                            color=su_color,
                            font_size=16,
                            font_weight="bold",
                            text_align="center",
                            z_index=10,
                        )
                   )

            # --- Right Column: Output/Preview ---
            with me.box(
                style=me.Style(
                    background="#ffffff",
                    padding=me.Padding.all(24),
                    border_radius=16,
                    box_shadow="0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    display="flex",
                    flex_direction="column",
                    gap=24,
                )
            ):
                me.text("Status & Output", style=me.Style(font_size=18, font_weight=600, color="#1e293b"))
                
                # Logs Area
                with me.box(
                    style=me.Style(
                        background="#f1f5f9",
                        flex_grow=1,
                        border_radius=8,
                        padding=me.Padding.all(16),
                        overflow_y="auto",
                        font_family="monospace",
                    )
                ):
                    if not state.logs:
                        me.text("Waiting for input...", style=me.Style(color="#94a3b8", font_style="italic"))
                    
                    for log in state.logs:
                        me.text(f"> {log}", style=me.Style(color="#334155", font_size=13, margin=me.Margin(bottom=8)))
                    
                    if state.processing_status == "analyzing":
                        with me.box(style=me.Style(display="flex", align_items="center", gap=8, margin=me.Margin(top=16))):
                            me.progress_spinner(diameter=20, stroke_width=2)
                            me.text("Reading & Analyzing...", style=me.Style(color="#2563eb", font_weight=500))

                    if state.processing_status == "generating":
                         with me.box(style=me.Style(display="flex", align_items="center", gap=8, margin=me.Margin(top=16))):
                            me.progress_spinner(diameter=20, stroke_width=2)
                            me.text("Designing Slides...", style=me.Style(color="#7c3aed", font_weight=500))

                    if state.processing_status == "analyzing_summary":
                        with me.box(style=me.Style(display="flex", align_items="center", gap=8, margin=me.Margin(top=16))):
                            me.progress_spinner(diameter=20, stroke_width=2)
                            me.text("Summarizing...", style=me.Style(color="#ea580c", font_weight=500))

                    if state.processing_status == "generating_pdf":
                         with me.box(style=me.Style(display="flex", align_items="center", gap=8, margin=me.Margin(top=16))):
                            me.progress_spinner(diameter=20, stroke_width=2)
                            me.text("Creating PDF...", style=me.Style(color="#db2777", font_weight=500))

                # Error Message
                if state.error_message:
                     with me.box(
                        style=me.Style(
                            background="#fef2f2",
                            padding=me.Padding.all(12),
                            border_radius=8,
                            border=me.Border.all(me.BorderSide(width=1, color="#fecaca")),
                        )
                    ):
                        me.text(f"Error: {state.error_message}", style=me.Style(color="#991b1b", font_size=14))

                # Download Section (Only show when done)
                if state.processing_status == "done":
                    with me.box(
                        style=me.Style(
                            background="#ecfdf5",
                            padding=me.Padding.all(24),
                            border_radius=12,
                            border=me.Border.all(me.BorderSide(width=1, color="#6ee7b7")),
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            gap=16,
                            text_align="center"
                        )
                    ):
                        me.icon("check_circle", style=me.Style(color="#059669", font_size=48))
                        me.text("Presentation Ready!", style=me.Style(font_size=20, font_weight=600, color="#065f46"))
                        
                        # Use me.html to create a download link with data URI
                        # since me.download isn't available/working as expected
                        data_uri = f"data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64,{state.pptx_content_base64}"
                        me.html(
                            f'<a href="{data_uri}" download="{state.pptx_filename}" '
                            'style="display: inline-block; background-color: #0284c7; color: white; '
                            'padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; font-family: Inter, sans-serif;">'
                            'Download PowerPoint'
                            '</a>'
                        )
                        
                        me.button(
                            "Create Another",
                            on_click=lambda e: setattr(state, "processing_status", "idle"),
                            style=me.Style(margin=me.Margin(top=16)),
                        )
                
                # Download Summary Section
                if state.processing_status == "summary_done":
                    with me.box(
                        style=me.Style(
                            background="#fff7ed",
                            padding=me.Padding.all(24),
                            border_radius=12,
                            border=me.Border.all(me.BorderSide(width=1, color="#fdba74")),
                            display="flex",
                            flex_direction="column",
                            align_items="center",
                            gap=16,
                            text_align="center"
                        )
                    ):
                        me.icon("description", style=me.Style(color="#ea580c", font_size=48))
                        me.text("Summary Ready!", style=me.Style(font_size=20, font_weight=600, color="#9a3412"))
                        
                        data_uri = f"data:application/pdf;base64,{state.pdf_content_base64}"
                        me.html(
                            f'<a href="{data_uri}" download="{state.pdf_filename}" '
                            'style="display: inline-block; background-color: #ea580c; color: white; '
                            'padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; font-family: Inter, sans-serif;">'
                            'Download Summary PDF'
                            '</a>'
                        )
                        
                        me.button(
                            "Start Over",
                            on_click=lambda e: setattr(state, "processing_status", "idle"),
                            style=me.Style(margin=me.Margin(top=16)),
                        )
