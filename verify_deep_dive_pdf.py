
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())

try:
    from summarizer import save_summary_to_pdf
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def verify_deep_dive_pdf_only():
    print("Verifying Deep Dive PDF Generation (Mock Data)...")
    
    # Mock Data behaving like the API output
    summary_data = {
        "mode": "deep_dive",
        "structure": "1. Introduction\n2. Methodology\n3. Results\n4. Conclusion",
        "details": """
# Chapter 1: Introduction
This is a detailed summary of the introduction. It covers the basic concepts of agents.

# Chapter 2: Methodology
The author discusses various search algorithms including A* and BFS.

*   **BFS**: Breadth-First Search
*   **A***: Heuristic Search

# Chapter 3: Results
The results show that informed search is better.
""",
        "synthesis": """
## Core Framework
The agents are rational.

## Critical Analysis
The book is comprehensive but dense.
""",
        "executive_overview": """
This book provides a foundational overview of AI. From agents to ethics, it covers it all.
The deep dive analysis confirms that the content is suitable for university students.
"""
    }

    try:
        output_pdf = "deep_dive_mock_report.pdf"
        pdf_path = save_summary_to_pdf(summary_data, output_pdf)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"SUCCESS: Mock Deep Dive PDF generated at {pdf_path}")
            print(f"Size: {os.path.getsize(pdf_path)} bytes")
        else:
            print("FAILED: PDF file empty or not found.")
            
    except Exception as e:
        print(f"PDF Generation FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_deep_dive_pdf_only()
