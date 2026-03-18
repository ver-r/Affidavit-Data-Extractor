# main.py
import sys
import json
from datetime import datetime

# pdf_to_images lives inside ocr_engine — no pdf_parser needed
from extractor.ocr_engine import pdf_to_images, extract_text_from_images
from extractor.field_extractor import extract_fields

from extractor.pan_validator import extract_pan
from database.schema import build_record
from database.mysql_handler import setup_database, insert_extraction


def process_pdf(pdf_path: str):
    print(f"\n{'='*50}")
    print(f" Processing: {pdf_path}")
    print(f"{'='*50}\n")

    # 1. PDF → images  (pdf_to_images is in ocr_engine.py)
    print("[1/4] Converting PDF pages to images...")
    images = pdf_to_images(pdf_path)

    # 2. Images → text blocks
    print("[2/4] Running OCR on all pages (this may take a minute)...")
    text_blocks = extract_text_from_images(images)

    # 3. Text → structured fields
    print("[3/4] Extracting fields...")
    fields = extract_fields(text_blocks)

    # 4. PAN extraction + validation
    print("[4/4] Extracting & validating PAN...")
    pan_result = extract_pan(text_blocks)
    print(f"      PAN found     : {pan_result.get('pan_number')}")
    print(f"      Valid         : {pan_result.get('is_valid')}")
    print(f"      Confidence    : {pan_result.get('confidence')}")

    # Build flat record and store in MySQL
    record = build_record(fields, pan_result, pdf_path)
    row_id = insert_extraction(record)

    # Pretty-print result
    output = {k: v for k, v in record.items() if v is not None}
    output["db_row_id"] = row_id
    output["extracted_at"] = str(output["extracted_at"])

    print("\n--- Extracted Output ---")
    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    pdf_path = r"E:\Affidavit-Data-Extractor\Affidavit-1765966076.pdf"

    # Creates DB + table automatically on first run
    setup_database()

    process_pdf(pdf_path)