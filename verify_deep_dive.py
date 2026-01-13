
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

try:
    from summarizer import summarize_book_deep_dive, save_summary_to_pdf
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

load_dotenv()

def verify_deep_dive():
    print("Starting Deep Dive Verification...")
    
    # Create a reasonably long dummy document to justify deep dive
    filename = "deep_dive_test.txt"
    mime_type = "text/plain"
    
    content = """
    INTELLIGENT AGENTS: A MODERN APPROACH
    
    Chapter 1: Introduction to Agents
    Agents are systems that perceive their environment and act upon it. An agent structure includes sensors, actuators, and the agent program.
    Rational agents strive to maximize their performance measure.
    
    Chapter 2: Problem Solving
    Problem solving agents use search algorithms to find sequences of actions that reach a goal.
    Uninformed search strategies (BFS, DFS) have no info about cost to goal.
    Informed search (A*, Greedy) use heuristics.
    
    Chapter 3: Knowledge Representation
    Logic is the primary vehicle for representing knowledge. Propositional logic is simple but limited. First-order logic allows objects and relations.
    Ontologies categorize the world.
    
    Chapter 4: Planning
    Planning agents use specific representations of states and actions. PDDL is a common language.
    Partial order planning vs Total order planning.
    
    Chapter 5: Artificial Neural Networks
    Perceptrons are the basic building blocks. Multi-layer perceptrons can approximate any function.
    Backpropagation is the key learning algorithm.
    Deep learning revolution changed the landscape with CNNs, RNNs, and Transformers.
    
    Chapter 6: Impact on Society
    AI safety, ethics, and bias are critical modern concerns.
    Automation and the workforce.
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    with open(filename, "rb") as f:
        file_bytes = f.read()

    print(f"1. Sending '{filename}' to Gemini (Deep Dive Mode)...")
    print("   Note: This involves 4 sequential API calls and might take 30-60 seconds.")
    
    try:
        summary_data = summarize_book_deep_dive(file_bytes, mime_type)
        
        print("\n--- Deep Dive Data Received ---")
        # Updated to check for Big Ideas Template keys
        required_keys = ["big_ideas", "introduction", "core_ideas", "about_author", "about_creator"]
        if not all(key in summary_data for key in required_keys):
            print("FAILED: Missing one or more required keys in Deep Dive response.")
            print(f"Keys found: {list(summary_data.keys())}")
            return
        
        if "metadata" not in summary_data:
            print("WARNING: 'metadata' key missing from response (Model ignored prompt). Using fallback.")
            
        print("Keys:", list(summary_data.keys()))
        print("Mode:", summary_data.get("mode"))
        print("Big Ideas Count:", len(summary_data.get("big_ideas", [])))
        print("Core Ideas Count:", len(summary_data.get("core_ideas", [])))
        
        if summary_data.get("mode") != "deep_dive":
             print("FAILED: Mode incorrect.")
             return

    except Exception as e:
        print(f"Summarization FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n2. Generating PDF report...")
    try:
        output_pdf = "deep_dive_report.pdf"
        pdf_path = save_summary_to_pdf(summary_data, output_pdf)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"SUCCESS: Deep Dive PDF generated at {pdf_path}")
            print(f"Size: {os.path.getsize(pdf_path)} bytes")
        else:
            print("FAILED: PDF file empty or not found.")
            
    except Exception as e:
        print(f"PDF Generation FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_deep_dive()
