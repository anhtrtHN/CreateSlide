from slide_engine import create_pptx
import base64

long_text = [
    "This is a very long point that will definitely take up more than one line " * 5,
    "Here is another extremely long point to consume vertical space " * 5,
    "Point number 3 is also quite verbose and verbose and verbose " * 5,
    "Fourth point adding to the pile of text to ensure we overflow constraints " * 5,
    "Final point to break the camel's back and push text outside the box " * 5
]

data = {
    "title": "Overflow Test Slide",
    "slides": [
        {
            "title": "This Title Is Fine",
            "content": long_text
        }
    ]
}

print("Generating slide with long text...")
pptx_io = create_pptx(data)
with open("test_overflow.pptx", "wb") as f:
    f.write(pptx_io.read())
print("Saved test_overflow.pptx")
