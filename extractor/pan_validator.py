#extractor/pan_validator.py
import re

PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

def validate_pan(pan):
    if not pan:
        return False
    return bool(PAN_PATTERN.match(pan))

def build_pan_result(pan, corrected=False):
    if not pan or not validate_pan(pan):
        return {
            "pan_number": None,
            "is_valid": False,
            "confidence": "low",
            "confidence_score": 0.0,
            "note": "PAN not found or invalid format"
        }

    score = 0.0
    if PAN_PATTERN.match(pan):       score += 0.4
    if pan[3] in ['P','C','H','F','A','T','B']: score += 0.2
    if pan[:3].isalpha():            score += 0.1
    if pan[4].isalpha():             score += 0.1
    if pan[5:9].isdigit():           score += 0.2

    score = round(min(score, 1.0), 2)
    confidence = "high" if score >= 0.8 else "medium" if score >= 0.6 else "low"
    note = "OCR corrected — manual verification recommended" if corrected else "Extracted cleanly"
    return {
        "pan_number": pan,
        "is_valid": True,
        "confidence": confidence,
        "confidence_score": score,
        "note": note
    }