import pdfplumber
import re

def extract_text_pages(pdf_path):
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text

def extract_name(page1):
    m = re.search(r'Purchased by\s*:?\s*([A-Z\s\.]{3,40})', page1)
    if m:
        name = m.group(1).strip()
        name = name.split("\n")[0]
        return name
    return None