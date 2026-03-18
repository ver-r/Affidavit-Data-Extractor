# pan_validator.py
import re

PAN_REGEX = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'

def extract_pan(text_blocks: list[str]) -> dict:
    for text in text_blocks:
        # Normalize OCR noise: O→0, I→1, l→1
        cleaned = text.upper()
        cleaned = cleaned.replace('O', '0').replace('I', '1')
        
        matches = re.findall(PAN_REGEX, cleaned)
        if matches:
            pan = matches[0]
            return {
                "pan_number": pan,
                "is_valid": validate_pan_checksum(pan),
                "confidence": "high" if len(matches) == 1 else "medium"
            }
    return {"pan_number": None, "is_valid": False, "confidence": "low"}

def validate_pan_checksum(pan: str) -> bool:
    # PAN structure rules:
    # 4th char = first letter of surname
    # 5th char = first letter of first name
    # 4th char for companies = P (for individuals)
    return bool(re.match(r'^[A-Z]{3}[ABCFGHLJPTK][A-Z][0-9]{4}[A-Z]$', pan))