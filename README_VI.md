# SlideGenius - AI Presentation Generator

SlideGenius là ứng dụng web sử dụng AI (Google Gemini) để tự động tạo bài thuyết trình PowerPoint (.pptx) từ các tài liệu nguồn như PDF, Word (.docx), hoặc Ebook (.epub).

Ứng dụng được xây dựng bằng **Python** và **Mesop**, với giao diện người dùng hiện đại và thân thiện.

## Yêu Cầu Hệ Thống

- **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux.
- **Python**: Phiên bản 3.10 trở lên (Khuyên dùng Python 3.12).
- **Google API Key**: Cần có API Key từ [Google AI Studio](https://aistudio.google.com/).

## Hướng Dẫn Cài Đặt

### 1. Cài đặt Python

Nếu chưa có Python, hãy tải và cài đặt từ trang chủ [python.org](https://www.python.org/downloads/) hoặc qua Microsoft Store.
**Lưu ý quan trọng**: Khi cài đặt trên Windows, hãy tích vào ô **"Add Python to PATH"**.

### 2. Tải Mã Nguồn

Tải về thư mục dự án này và mở terminal (Command Prompt hoặc PowerShell) tại thư mục đó.

### 3. Cài Đặt Thư Viện

Chạy lệnh sau để cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

Nếu bạn gặp lỗi "pip not recognized", hãy thử: `python -m pip install -r requirements.txt` hoặc `py -m pip install -r requirements.txt`.

## Cấu Hình

Bạn cần thiết lập Google API Key để ứng dụng có thể kết nối với AI.

1.  Tạo một file có tên `.env` trong cùng thư mục với `main.py` (nếu chưa có).
2.  Mở file `.env` bằng Notepad hoặc trình soạn thảo code.
3.  Thêm dòng sau vào file, thay thế `YOUR_API_KEY` bằng key thực của bạn:

```env
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```
*(Thay thế mã trên bằng mã API của chính bạn)*

## Chạy Ứng Dụng

Sau khi cài đặt xong, khởi chạy ứng dụng bằng lệnh:

```bash
python main.py
```
Hoặc nếu dùng Mesop trực tiếp:
```bash
mesop main.py
```

Ứng dụng sẽ khởi động và hiển thị đường dẫn truy cập, thường là:
**http://localhost:32123**

Hãy mở đường dẫn này trên trình duyệt web để bắt đầu sử dụng.

## Hướng Dẫn Sử Dụng

1.  **Input Documents**: Tải lên file tài liệu bạn muốn chuyển thành slide (PDF, DOCX, EPUB).
2.  **Slide Template (Tùy chọn)**: Tải lên file mẫu PowerPoint (.pptx) nếu bạn muốn dùng giao diện riêng.
3.  **Topic (Tùy chọn)**: Nhập chủ đề để AI định hướng nội dung tốt hơn.
4.  **Chế độ**: Chọn "Chi tiết (Deep Dive)" nếu muốn nội dung sâu, nhiều slide hơn.
5.  Nhấn **Generate Slides** và đợi AI xử lý.
6.  Khi hoàn tất, nhấn nút **Download PowerPoint** để tải về.
