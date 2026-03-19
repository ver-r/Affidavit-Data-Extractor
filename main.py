import sys
import json
from datetime import datetime

from extractor.ocr_engine import pdf_to_images, extract_text_from_images
from extractor.ner_extractor import run_ner
from extractor.field_extractor import extract_regex_fields, merge_fields
from extractor.pan_validator import extract_pan

from database.schema import build_record
from database.mysql_handler import setup_database, insert_extraction


def process_pdf(pdf_path):

    print("\nProcessing:", pdf_path)

    # OCR
    images = pdf_to_images(pdf_path)
    text_blocks = extract_text_from_images(images)
    important_pages = []

    if len(text_blocks) >= 1:
        important_pages.append(text_blocks[0])  # page 1

    if len(text_blocks) >= 2:
        important_pages.append(text_blocks[1])  # page 2

    if len(text_blocks) >= 11:
        important_pages.append(text_blocks[10])  # page 11

    focused_text = important_pages
    # NER
    ner_fields = run_ner(focused_text)
    print("NER:", ner_fields)

    # REGEX
    regex_fields = extract_regex_fields(focused_text)
    print("REGEX:", regex_fields)

    fields = merge_fields(regex_fields, ner_fields)

    # PAN
    pan_result = extract_pan(focused_text)

    print("PAN:", pan_result)

    record = build_record(
        extracted=fields,
        pan_result=pan_result,
        source_file=pdf_path,
        ocr_engine="tesseract"
    )

    row_id = insert_extraction(record)

    output = record.copy()
    output["db_row_id"] = row_id
    output["extracted_at"] = str(datetime.now())

    print(json.dumps(output, indent=2))

    return output


if __name__ == "__main__":

    pdf_path =r"E:\Affidavit-Data-Extractor\Affidavit-1773840643.pdf"
    setup_database()

    process_pdf(pdf_path)