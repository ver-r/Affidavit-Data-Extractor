# ocr_engine.py
import fitz  # PyMuPDF
import easyocr
from PIL import Image
import io
import numpy as np

def pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    return images

def extract_text_from_images(images):
    reader = easyocr.Reader(['hi', 'en'])  # Hindi + English
    all_text = []
    for img in images:
        img_array = np.array(img)
        result = reader.readtext(img_array, detail=0)
        all_text.append(" ".join(result))
    return all_text