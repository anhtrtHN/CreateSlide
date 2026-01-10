# SlideGenius - AI Presentation Generator

SlideGenius is an intelligent web application that leverages Google Gemini AI to automatically generate professional PowerPoint presentations (`.pptx`) from various source documents such as PDF, Word (`.docx`), or EBooks (`.epub`).

Built with **Python** and **Mesop**, it features a modern and user-friendly interface.

## System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux.
- **Python**: Version 3.10 or higher (Python 3.12 Recommended).
- **Google API Key**: Required from [Google AI Studio](https://aistudio.google.com/).

## Installation Guide

### 1. Install Python

If not already installed, download Python from [python.org](https://www.python.org/downloads/) or via the Microsoft Store.
**Important**: On Windows, check the box **"Add Python to PATH"** during installation.

### 2. Download Source Code

Clone this repository or download the source code and open a terminal (Command Prompt or PowerShell) in the project directory.

### 3. Install Dependencies

Run the following command to install the required libraries:

```bash
pip install -r requirements.txt
```

If you encounter a "pip not recognized" error, try: `python -m pip install -r requirements.txt` or `py -m pip install -r requirements.txt`.

## Configuration

You must configure your Google API Key for the application to connect to the AI model.

1.  Create a file named `.env` in the same directory as `main.py` (if it doesn't exist).
2.  Open `.env` with Notepad or a code editor.
3.  Add the following line, replacing `YOUR_API_KEY` with your actual key:

```env
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```
*(Replace the code above with your own API key)*

## Running the Application

After installation, launch the application using the command:

```bash
python main.py
```
Or if using Mesop directly:
```bash
mesop main.py
```

The application will start and display an access URL, typically:
**http://localhost:32123**

Open this URL in your web browser to start using the tool.

## User Guide

1.  **Input Documents**: Upload the document you want to convert into slides (PDF, DOCX, EPUB).
2.  **Slide Template (Optional)**: Upload a PowerPoint template file (`.pptx`) if you want to use a custom design.
3.  **Topic (Optional)**: Enter a topic to help the AI better orient the content.
4.  **Mode**: Select "Chi tiết (Deep Dive)" if you want deeper content and more slides.
5.  Click **Generate Slides** and wait for the AI to process.
6.  Once complete, click the **Download PowerPoint** button to download the file.

## Features

- **Multi-Format Support**: Handles PDF, DOCX, and EPUB files.
- **Smart Layout**: Automatically calculates title heights and spacing for a balanced look.
- **Resilient AI**: Includes smart fallback mechanisms (Retry with exponential backoff, model switching) to handle API rate limits.
- **Custom Templates**: fully supports user-provided PowerPoint templates.

---
*For Vietnamese instructions, please refer to [README_VI.md](README_VI.md).*
