import re

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

def validate_pan(pan):
    if not pan:
        return False
    return bool(PAN_PATTERN.match(pan))

def build_pan_result(pan):
    if validate_pan(pan):
        return {
            "pan_number": pan,
            "is_valid": True,
            "confidence": "high",
            "confidence_score": 0.95
        }
    return {
        "pan_number": None,
        "is_valid": False,
        "confidence": "low",
        "confidence_score": 0
    }