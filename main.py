# main.py

import os
import re
import glob
from extractor.pdf_extractor import extract_text_pages, extract_name
from extractor.field_extractor import extract_fields
from extractor.ocr_extractor import run_ocr, run_ocr_groq
from extractor.pan_validator import build_pan_result
from utils.transliterate import tamil_to_english
from utils.csv_writer import write_csv
from utils.logger import get_logger
from database.schema import build_record
from database.mysql_handler import insert_extraction
from database.mysql_handler import setup_database

log = get_logger()
setup_database()


def process_pdf(pdf_path):

    log.info(f"Processing: {pdf_path}")
    '''
    pdf_text = extract_text_pages(pdf_path)
    log.info(f"pdfplumber text sample: {pdf_text[1000:2000]}")
    name = extract_name(pdf_text)
    ocr_engine = "pdfplumber"
    
    total_chars = len(pdf_text.strip())
    english_chars = len(re.findall(r'[a-zA-Z]', pdf_text))
    english_ratio = english_chars / total_chars if total_chars > 0 else 0

    log.info(f"English ratio: {english_ratio:.2f}") 
    if len(pdf_text.strip()) < 200 or  english_ratio<0.3:
        log.info("Poor text from pdfplumber, trying Tesseract...")
        ocr_engine = "tesseract"
        ocr_text = run_ocr(pdf_path)
        ocr_text = tamil_to_english(ocr_text)
        combined_text = pdf_text + "\n" + ocr_text

        pan_found = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', combined_text)

        if not pan_found:
            log.info("No PAN after Tesseract, trying Groq...")
            ocr_engine = "groq"
            groq_text = run_ocr_groq(pdf_path)
            log.info(f"Groq raw text preview: {groq_text[:300]}")
            combined_text = combined_text + "\n" + groq_text
            log.info("Groq extraction complete.")
    else:
        log.info("Good text from pdfplumber, skipping OCR.")
        combined_text = pdf_text'''
    
    # in process_pdf - remove the if/else condition entirely
# always combine both pdfplumber and tesseract

    pdf_text = extract_text_pages(pdf_path)
    name = extract_name(pdf_text)
    ocr_engine = "tesseract"

    log.info("Running OCR to supplement pdfplumber...")
    ocr_text = run_ocr(pdf_path)
    ocr_text = tamil_to_english(ocr_text)
    combined_text = pdf_text + "\n" + ocr_text

    pan_found = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', combined_text)

    if not pan_found:
        log.info("No PAN after Tesseract, trying Groq...")
        ocr_engine = "groq"
        groq_text = run_ocr_groq(pdf_path)
        log.info(f"Groq raw text preview: {groq_text[:300]}")
        combined_text = combined_text + "\n" + groq_text
        log.info("Groq extraction complete.")
    fields = extract_fields(combined_text)

    
    all_pans = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', combined_text)
    log.info(f"All PANs found in order: {all_pans}")  ###remove this CODE PLS.
    result = {"full_name": name, **fields}
    pan_result = build_pan_result(
    fields.get("pan_number"),
    corrected=fields.get("pan_corrected", False)
)

    log.info(f"Extracted: {result}")
    log.info(f"PAN validation: {pan_result}")

    return result, pan_result, ocr_engine  # also return engine used


def main():

    current_folder = os.path.dirname(os.path.abspath(__file__))
    pdf_files = glob.glob(os.path.join(current_folder, "*.pdf"))

    if not pdf_files:
        log.warning("No PDFs found in folder.")
        return

    log.info(f"Found {len(pdf_files)} PDFs")
    all_records = []

    for pdf in pdf_files:
        try:
            extracted, pan_result, ocr_engine = process_pdf(pdf)  # unpack 3 values

            if not pan_result.get("pan_number"):
                log.warning(
            f"Skipping {os.path.basename(pdf)} — "
            f"No PAN found. Possible reasons: different format, "
            f"nomination document, or non-ECI affidavit."
                )
                continue

            record = build_record(
                extracted=extracted,
                pan_result=pan_result,
                source_file=os.path.basename(pdf),
                ocr_engine=ocr_engine  # fixed: was "ocr_engine" string before
            )

            insert_extraction(record)
            all_records.append(record)

        except Exception as e:
            log.error(f"Failed to process {pdf}: {e}")

    if all_records:
        write_csv(all_records, output_dir=current_folder)
        log.info(f"CSV written with {len(all_records)} records.")
    else:
        log.warning("No records to write.")


if __name__ == "__main__":
    main()
