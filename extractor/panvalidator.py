# extractor/pan_validator.py
import re

PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')

# These strings look like PAN but are not
FALSE_POSITIVES = {"COMMI5510N"}


def validate_pan(pan: str) -> bool:
    if not pan or len(pan) != 10:
        return False
    return bool(PAN_PATTERN.match(pan))


def build_pan_result(pan_number: str | None) -> dict:
    """
    Takes a PAN string already extracted by pdf_extractor
    and returns the standard result dict expected by schema.py
    """
    if pan_number and pan_number not in FALSE_POSITIVES and validate_pan(pan_number):
        return {
            "pan_number":       pan_number,
            "is_valid":         True,
            "confidence":       "high",
            "confidence_score": 0.95,
        }
    return {
        "pan_number":       None,
        "is_valid":         False,
        "confidence":       "low",
        "confidence_score": 0,
    }