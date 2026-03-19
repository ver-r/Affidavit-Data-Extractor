import pypdfium2 as pdfium
import pytesseract

def run_ocr(pdf_path):
    doc = pdfium.PdfDocument(pdf_path)
    text = ""
    for page in doc:
        bitmap = page.render(scale=300/72)
        img = bitmap.to_pil()
        page_text = pytesseract.image_to_string(
            img,
            lang="eng+hin+tam",
            config="--psm 6"
        )
        text += page_text + "\n"
    doc.close()
    return text