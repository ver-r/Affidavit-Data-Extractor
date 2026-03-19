# database/schema.py
from datetime import datetime


def build_record(
    extracted:   dict,
    pan_result:  dict,
    source_file: str,
    ocr_engine:  str = "tesseract",   # passed in from main.py — never hardcoded
) -> dict:
    """
    Flattens extracted fields + PAN result into a flat dict
    that maps 1-to-1 with the MySQL table columns.
    """
    return {
        # Source
        "source_file":         source_file,
        "extracted_at":        datetime.utcnow(),

        # Personal (from NER)
        "full_name":           extracted.get("full_name"),
        "fathers_name":        extracted.get("fathers_name"),
        "age":                 extracted.get("age"),
        "address":             extracted.get("address"),
        "mobile":              extracted.get("mobile"),

        # Election (from regex)
        "constituency_number": extracted.get("constituency_number"),
        "constituency_name":   extracted.get("constituency_name"),      # NER field name
        "affidavit_number":    extracted.get("affidavit_number"),

        # PAN (from pan_validator)
        "pan_number":          pan_result.get("pan_number"),
        "pan_valid":           1 if pan_result.get("is_valid") else 0,
        "pan_confidence":      pan_result.get("confidence", "low"),

        # Metadata — ocr_engine is passed in, NEVER hardcoded
        "ocr_engine":          ocr_engine,
        "extraction_status": (
        "success" if pan_result.get("pan_number") and extracted.get("full_name")
        else "failed" if not extracted.get("full_name") and not pan_result.get("pan_number")
        else "partial"
),
    }