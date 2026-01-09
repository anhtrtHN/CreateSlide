from slide_engine import create_pptx
import os

# Create a slide with standard title and long-ish content to check gap and overflow
data = {
    "title": "Title For Layout Check",
    "slides": [
        {
            "title": "Checking Gap Distance & Overflow",
            "content": [
                "This is point 1 to check the vertical gap from title.",
                "This is point 2. The user said the gap was too large.",
                "This is point 3. We moved the body box UP.",
                "This is point 4. Also checking if **keyword highlighting** works correctly.",
                "Point 5: " + "This text is deliberately long to test the wrapping " * 3,
                "Point 6: Another long point to force edge cases " * 2
            ]
        }
    ]
}

print("Generating layout test...")
pptx_io = create_pptx(data)
with open("test_layout_adjusted.pptx", "wb") as f:
    f.write(pptx_io.read())
print("Saved test_layout_adjusted.pptx")
