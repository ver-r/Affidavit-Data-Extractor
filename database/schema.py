# database/schema.py
from datetime import datetime

def build_record(
    extracted:   dict,
    pan_result:  dict,
    source_file: str,
    ocr_engine:  str = "tesseract",   
) -> dict:
    return {
        # Source
        "source_file":         source_file,
        "extracted_at":        datetime.utcnow(),

        # Personal
        "full_name":           extracted.get("full_name"),
        "fathers_name":        extracted.get("fathers_name"),
        "age":                 extracted.get("age"),
        "address":             extracted.get("address"),
        "mobile":              extracted.get("mobile"),

        # Election
        "constituency_number": extracted.get("constituency_number"),
        "constituency_name":   extracted.get("constituency_name"),      
        "affidavit_number":    extracted.get("affidavit_number"),

        # PAN 
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