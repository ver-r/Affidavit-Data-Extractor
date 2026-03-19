# main.py
import os
import json
import glob

from database.mysql_handler import setup_database, insert_extraction
from database.schema import build_record
from extractor.pdf_extractor import extract_all_fields
from extractor.ocr_extractor import extract_via_ocr
from extractor.panvalidator import build_pan_result

# Folder where PDFs live — change if needed
PDF_FOLDER = os.path.dirname(os.path.abspath(__file__))


def process_pdf(pdf_path: str) -> dict:
    print(f"\nProcessing: {pdf_path}")

    # Step 1: pdfplumber — fast, works perfectly on digital PDFs
    extracted = extract_all_fields(pdf_path)

    # Step 2: OCR fallback — fills gaps using pypdfium2 + tesseract (no poppler)
    #   - Page 2 OCR  → mobile, age, email, constituency
    #   - Last pages  → rule-based NER for name/father/address
    extracted = extract_via_ocr(pdf_path, extracted)

    # Step 3: PAN result
    pan_result = build_pan_result(extracted.get("pan_number"))

    print(f"  Name        : {extracted.get('full_name')}")
    print(f"  Father      : {extracted.get('fathers_name')}")
    print(f"  Age         : {extracted.get('age')}")
    print(f"  Address     : {extracted.get('address')}")
    print(f"  Mobile      : {extracted.get('mobile')}")
    print(f"  Email       : {extracted.get('email')}")
    print(f"  PAN         : {pan_result}")
    print(f"  Constituency: {extracted.get('constituency_name')} ({extracted.get('constituency_number')})")

    # Step 4: Build DB record and insert
    record = build_record(
        extracted=extracted,
        pan_result=pan_result,
        source_file=pdf_path,
        ocr_engine="pdfplumber+tesseract",
    )
    row_id = insert_extraction(record)
    record["db_row_id"] = row_id
    return record


def main():
    setup_database()

    pdf_files = sorted(glob.glob(os.path.join(PDF_FOLDER, "*.pdf")))
    if not pdf_files:
        print(f"No PDF files found in: {PDF_FOLDER}")
        return

    for pdf_path in pdf_files:
        try:
            result = process_pdf(pdf_path)
            print("\nRecord saved:")
            print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"[ERROR] {pdf_path}: {e}")
            import traceback; traceback.print_exc()

    print(f"\nDone. Processed {len(pdf_files)} file(s).")


if __name__ == "__main__":
    main()