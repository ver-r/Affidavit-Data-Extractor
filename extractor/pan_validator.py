from pydoc import text
import re
from collections import Counter


PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')


def validate_pan(pan):

    if not pan:
        return False

    if len(pan) != 10:
        return False

    return bool(PAN_PATTERN.match(pan))


def extract_pan(text_blocks):

    text = "\n".join(text_blocks)

    # remove spaces/newlines
    

    # detect PAN
    # Try original text first, then cleaned fallback
    matches = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', text)
    if not matches:
        cleaned = re.sub(r'\s+', '', text)
        matches = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', cleaned)
    if not matches:
        # Try 3: fix O→0 substitution then match (OCR artifact)
        import re as _re
        def ocr_fix(m):
            s = m.group(0)
            # Only fix digit positions (index 5-8)
            chars = list(s)
            for i in range(5, 9):
                chars[i] = chars[i].replace('O','0').replace('o','0').replace('I','1').replace('l','1')
            return ''.join(chars)
        fixed = _re.sub(r'[A-Z]{5}[A-Za-z0-9]{4}[A-Z]', ocr_fix, text)
        matches = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', fixed)
    

    if not matches:
        return {
            "pan_number": None,
            "is_valid": False,
            "confidence": "low",
            "confidence_score": 0
        }

    pan = matches[0]

    return {
        "pan_number": pan,
        "is_valid": True,
        "confidence": "high",
        "confidence_score": 0.9
    }