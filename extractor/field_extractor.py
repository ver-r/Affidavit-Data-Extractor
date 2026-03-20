# extractor/field_extractor.py
import re

def clean_ocr_pan(text):
    replacements = {
        '0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B',
    }
    pans = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', text)
    if pans:
        return pans, False
    candidates = re.findall(r'[A-Z0-9]{10}', text)
    valid = []
    for c in candidates:
        fixed = list(c)
        for i in [0, 1, 2, 3, 4, 9]:
            if fixed[i].isdigit():
                fixed[i] = replacements.get(fixed[i], fixed[i])
        for i in [5, 6, 7, 8]:
            if fixed[i].isalpha():
                for orig, rep in replacements.items():
                    if fixed[i] == rep:
                        fixed[i] = orig
        fixed = ''.join(fixed)
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', fixed):
            valid.append(fixed)
    return valid, True

def extract_candidate_pan(text):
    pans, corrected = clean_ocr_pan(text)
    if not pans:
        return None, False
    if len(pans) == 1:
        return pans[0], corrected
    pan_positions = [(text.find(p), p) for p in pans if text.find(p) != -1]
    pan_positions.sort(key=lambda x: x[0])
    row1_match = re.search(
        r'(?:^|\n)\s*1[\.\s]\s*[^\n]{0,150}?([A-Z]{5}[0-9]{4}[A-Z])',
        text, re.MULTILINE
    )
    if row1_match:
        return row1_match.group(1), corrected  
    self_match = re.search(r'\bself\b', text, re.I)
    if self_match:
        for pos, pan in pan_positions:
            if pos > self_match.start():
                return pan, corrected  
    return (pan_positions[0][1] if pan_positions else None), corrected

def extract_fields(text):
    result = {
        "age": None,
        "mobile": None,
        "email": None,
        "pan_number": None,
        "pan_corrected": False,
        "address": None,
        "constituency_name": None,
        "constituency_number": None,
        "fathers_name": None,
    }

    # MOBILE
    mobiles = re.findall(r'\b[6-9]\d{9}\b', text)
    if mobiles:
        result["mobile"] = mobiles[0]
        pos = text.find(mobiles[0])
        start = max(0, pos - 400)
        end = pos + 1500
        local_text = text[start:end]
    else:
        local_text = text

    # EMAIL
    emails = re.findall(
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        local_text
    )
    if emails:
        result["email"] = emails[0]

    # AGE
    age_patterns = [
        r'aged\s+(\d{2})\s*years',
        r'(\d{2})\s*years\s*(?:of\s*age)?',
        r'age[d]?\s*[:\-]?\s*(\d{2})',
        r'(\d{2})\s*(?:years|yrs)',
    ]
    for pat in age_patterns:
        m = re.search(pat, local_text, re.I)
        if m:
            age = int(m.group(1))
            if 18 <= age <= 100:
                result["age"] = age
                break

    # PAN
    pan, corrected = extract_candidate_pan(text)
    result["pan_number"] = pan
    result["pan_corrected"] = corrected

    # ADDRESS
    addr_match = re.search(
        r'(?:residing at|resident of)\s+(No\.?\s*[^.\n]{10,120})',
        text, re.I
    )
    if addr_match:
        result["address"] = re.sub(r'\s+', ' ', addr_match.group(1)).strip()

    # CONSTITUENCY
    patterns = [
        r'from\s+(\d+)[,\.]?\s*([A-Za-z][A-Za-z\s]+?)\s+[Cc]onstituency',
        r'election\s+from\s+(\d+)[,\.]?\s*([A-Za-z][A-Za-z\s]+?)\s+[Cc]onstituency',
        r'[Cc]onstituency[^\n]*?(\d+)[,\.]?\s*([A-Za-z][A-Za-z\s]+?)\s*[\n,\.]',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            result["constituency_number"] = m.group(1)
            result["constituency_name"] = m.group(2).strip()
            break

    # FATHER/SPOUSE NAME
    parent_patterns = [
        r'[Ss]/[Oo]\.?\s+([A-Z][a-zA-Z\s\.]{3,40})',
        r'[Ss]on\s+of\s+(?:Mr\.?\s*)?([A-Z][a-zA-Z\s\.]{3,40})',
        r'[Ww]ife\s+of\s+(?:Mr\.?\s*)?([A-Z][a-zA-Z\s\.]{3,40})',
        r'[Hh]usband\s+of\s+(?:Mr\.?\s*)?([A-Z][a-zA-Z\s\.]{3,40})',
        r'[Dd]/[Oo]\.?\s+([A-Z][a-zA-Z\s\.]{3,40})',
        r'[Ww]/[Oo]\.?\s+([A-Z][a-zA-Z\s\.]{3,40})',
    ]
    for pat in parent_patterns:
        father_match = re.search(pat, text)
        if father_match:
            result["fathers_name"] = father_match.group(1).strip().split("\n")[0]
            break

    return result 