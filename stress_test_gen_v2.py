
import io
import json
from slide_engine import create_pptx

# Define Worst-Case Scenarios
scenarios = {
    "title": "STRESS TEST REPORT (FIXED)",
    "slides": [
        {
            "title": "CASE 1: The Ideal (Short)",
            "content": [
                "This is a standard slide.",
                "Title is short (< 50 chars).",
                "Content is moderate.",
                "Expectation: Title Height ~2.0cm, Gap 0.4cm, Body starts high."
            ]
        },
        {
            "title": "CASE 2: The Double Decker (Long Title > 50 chars) which should trigger the larger height calculation logic automatically",
            "content": [
                "Title is very long.",
                "Expectation: Title Height increases significantly (automata).",
                "Body should be pushed down."
            ]
        },
        {
            "title": "CASE 3: The Text Wall (Overflow Risk)",
            "content": [
                "This slide has a HUGE amount of text to test font scaling and boundary safety.",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
                "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.",
                "Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.",
                "Strategy: Font size should shrink, but Text Box must NOT overlap Title or fall off the slide."
            ]
        },
        {
            "title": "CASE 4: The Nightmare (Long Title + Huge Text)",
            "title_override": "This is a very long title that surely takes two lines of text to test the layout engine capabilities fully combined with heavy body text",
            "content": [
                "Title takes 2 lines.",
                "Body is massive.",
                "This is the ultimate collision test.",
                "Checking gap integrity...",
                "Checking bottom margin integrity...",
                "Checking font scaling...",
                "The system should handle this gracefully without overlap."
            ]
        }
    ]
}

# Override title for case 4 in the loop or manual fix
# Since the engine takes json, let's just use the long string in the dict
scenarios['slides'][3]['title'] = scenarios['slides'][3]['title_override']

print("Generating Stress Test FIXED PPTX...")
pptx_io = create_pptx(scenarios)

# Save to NEW file to avoid permission error
with open("stress_test_fixed.pptx", "wb") as f:
    f.write(pptx_io.read())

try:
    print("Done. Saved to stress_test_fixed.pptx")
except:
    pass
