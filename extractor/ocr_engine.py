# extractor/ocr_engine.py

import fitz
import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# Tamil digit conversion
TAMIL_DIGITS = {
    "௦": "0",
    "௧": "1",
    "௨": "2",
    "௩": "3",
    "௪": "4",
    "௫": "5",
    "௬": "6",
    "௭": "7",
    "௮": "8",
    "௯": "9",
}


def normalize_digits(text):
    for t, d in TAMIL_DIGITS.items():
        text = text.replace(t, d)
    return text
def fix_ocr_substitutions(text):
    """Fix common OCR letter/digit confusion in PAN context."""
    import re
    def replace_in_pan_context(m):
        s = m.group(0)
        s = s.replace('O', '0').replace('o', '0')  # letter O → digit 0
        s = s.replace('I', '1').replace('l', '1')  # letter I/l → digit 1
        s = s.replace('S', '5')                    # letter S → digit 5
        return s
    # Only apply substitutions in the digit portion of PAN (positions 6-9)
    text = re.sub(r'[A-Z]{5}[A-Z0-9Ool1S]{4}[A-Z]', replace_in_pan_context, text)
    return text

def preprocess(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2)
    img = ImageEnhance.Sharpness(img).enhance(2)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageOps.autocontrast(img)
    return img


def pdf_to_images(pdf_path, dpi=400):

    doc = fitz.open(pdf_path)
    images = []

    for page in doc[:4]:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img = preprocess(img)
        images.append(img)

    doc.close()
    return images


def extract_text_from_images(images):

    all_text = []

    for i, img in enumerate(images):

        text = pytesseract.image_to_string(
            img,
            lang="eng+tam",
            config="--psm 3 --oem 3"
        )

        text = normalize_digits(text)
        text = fix_ocr_substitutions(text)
        print(f"\n--- OCR PAGE {i+1} SAMPLE ---")
        print(text[:200])

        all_text.append(text)

    return all_text