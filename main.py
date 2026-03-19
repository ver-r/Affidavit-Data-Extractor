import os
import glob
from extractor.pdf_extractor import extract_text_pages, extract_name
from extractor.field_extractor import extract_fields
from extractor.ocr_extractor import run_ocr
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
    
    pdf_text = extract_text_pages(pdf_path)
    name = extract_name(pdf_text)
    ocr_text = run_ocr(pdf_path)
    ocr_text = tamil_to_english(ocr_text)
    combined_text = pdf_text + "\n" + ocr_text
    fields = extract_fields(combined_text)
    result = {
        "full_name": name,
        **fields
    }
    pan_result = build_pan_result(fields.get("pan_number"))

    log.info(f"Extracted: {result}")
    log.info(f"PAN validation: {pan_result}")

    return result, pan_result


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
            extracted, pan_result = process_pdf(pdf)
            if not pan_result.get("pan_number"):
                log.warning(f"No PAN found in {os.path.basename(pdf)}, skipping DB insert.")
                continue
            record = build_record(
                extracted=extracted,
                pan_result=pan_result,
                source_file=os.path.basename(pdf),
                ocr_engine="tesseract"
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