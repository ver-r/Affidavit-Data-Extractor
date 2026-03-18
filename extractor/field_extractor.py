# field_extractor.py
import re

def extract_fields(text_blocks: list[str]) -> dict:
    full_text = " ".join(text_blocks)
    
    data = {
        "full_name": None,
        "fathers_name": None,
        "address": None,
        "age": None,
        "constituency": None,
        "affidavit_number": None,
        "mobile": None,
        "pan_number": None,
    }

    # Name — typically appears after "मैं" (I) in the affidavit
    name_match = re.search(r'(?:I am|मैं)\s+([A-Za-z\s]+)\s+s/o|d/o|w/o', full_text, re.IGNORECASE)
    if name_match:
        data["full_name"] = name_match.group(1).strip()

    # Mobile number
    mobile_match = re.search(r'\b[6-9]\d{9}\b', full_text)
    if mobile_match:
        data["mobile"] = mobile_match.group()

    # Age
    age_match = re.search(r'(?:age|आयु)[^\d]*(\d{2})', full_text, re.IGNORECASE)
    if age_match:
        data["age"] = int(age_match.group(1))

    # Affidavit number
    aff_match = re.search(r'AFFIDAVIT\s*No[.\s]*(\d+)', full_text, re.IGNORECASE)
    if aff_match:
        data["affidavit_number"] = aff_match.group(1)

    return data