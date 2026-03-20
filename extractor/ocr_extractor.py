# extractor/ocr_extractor.py
import re
import pypdfium2 as pdfium
import pytesseract
import base64
import io
import time
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def run_ocr(pdf_path):
    doc = pdfium.PdfDocument(pdf_path)
    text = ""
    for page in doc:
        bitmap = page.render(scale=150/72)
        img = bitmap.to_pil()
        page_text = pytesseract.image_to_string(
            img,
            lang="eng+tam+hin",
            config="--psm 6"
        )
        text += page_text + "\n"
    doc.close()
    return text

def run_ocr_groq(pdf_path):
    doc = pdfium.PdfDocument(pdf_path)
    all_text = ""

    for i, page in enumerate(doc):
        if i >= 3:  # only first 3 pages
            break

        bitmap = page.render(scale=150/72)
        img = bitmap.to_pil()

        # convert PIL image to base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        try:
            response = groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all text from this affidavit page. Return plain text only, no formatting or explanation."
                        }
                    ]
                }]
            )
            all_text += response.choices[0].message.content + "\n" 
            time.sleep(1) 
        except Exception as e:
            print(f"[groq] Page {i} error: {e}")
            time.sleep(3)
            continue
    doc.close()
    return all_text