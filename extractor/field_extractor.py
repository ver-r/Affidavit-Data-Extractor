import re


def extract_regex_fields(text_blocks):

    text = "\n".join(text_blocks)

    data = {}

    # -----------------------
    # Name + Father Name
    # -----------------------
    match = re.search(
    r'([A-Z][a-zA-Z\s\.]+),?\s*S/o\.?\s*([A-Z][a-zA-Z\s]+)',
    text
)
    if not match:
    # Fallback: notarial cert format "certify that L. SAMBATH son of Mr. Leela Sekar"
        match = re.search(
        r'certify that\s+([A-Z][A-Z\s\.]+)\s+son of\s+(?:Mr\.\s*)?([A-Z][a-zA-Z\s]+),',
        text
    )

    if match:
        data["full_name"] = match.group(1).strip()
        data["fathers_name"] = match.group(2).strip()

    # -----------------------
    # Age
    # -----------------------
    age_match = re.search(r'aged\s*(\d{2})', text, re.I)
    if not age_match:
        age_match = re.search(r',\s*aged\s+(\d{1,3})\s+years', text, re.I)
    if age_match:
        data["age"] = int(age_match.group(1))

    # -----------------------
    # Address
    # -----------------------
    addr_match = re.search(
    r'resident of\s*(.*?\d{3}\s*\d{3})',
    text,
    re.I | re.S
    )

    if addr_match:
        data["address"] = addr_match.group(1).replace("\n", " ")

    # -----------------------
    # PAN
    # -----------------------
    pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)

    if pan_match:
        data["pan_number"] = pan_match.group(0)

    # -----------------------
    # Mobile
    # -----------------------
    mobile_match = re.search(r'\b[6-9]\d{9}\b', text)

    if mobile_match:
        data["mobile"] = mobile_match.group(0)

    # -----------------------
    # Email
    # -----------------------
    email_match = re.search(
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        text
    )

    if email_match:
        data["email"] = email_match.group(0)

    return data
def merge_fields(regex_fields, ner_fields):

    merged = regex_fields.copy()

    for key, value in ner_fields.items():
        if value and key not in merged:
            merged[key] = value

    return merged