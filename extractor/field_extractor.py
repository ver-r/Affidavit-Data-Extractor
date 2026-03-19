import re

def extract_fields(text):

    result = {
        "age": None,
        "mobile": None,
        "email": None,
        "pan_number": None,
        "address": None,
        "constituency_name": None,
        "constituency_number": None
    }

    # ---------------------------
    # MOBILE (anchor)
    # ---------------------------
    mobiles = re.findall(r'\b[6-9]\d{9}\b', text)

    if mobiles:
        result["mobile"] = mobiles[0]

        # create local window around the mobile
        pos = text.find(mobiles[0])
        start = max(0, pos - 400)
        end = pos + 1500

        local_text = text[start:end]

    else:
        local_text = text


    # ---------------------------
    # EMAIL
    # ---------------------------
    emails = re.findall(
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        local_text
    )

    if emails:
        result["email"] = emails[0]


    # ---------------------------
    # AGE
    # ---------------------------
    m = re.search(r'(\d{2})\s*(?:years|yrs|aged)', local_text, re.I)

    if m:
        age = int(m.group(1))
        if 18 <= age <= 100:
            result["age"] = age


    # ---------------------------
    # PAN (search whole document)
    # ---------------------------
    pans = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', text)

    if pans:
        result["pan_number"] = pans[0]


    # ---------------------------
    # ADDRESS (pincode anchor)
    # ---------------------------
    '''
    pin_match = re.search(r'\b\d{6}\b', text)

    if pin_match:
        pos = pin_match.start()

        start = max(0, pos - 120)
        end = pos + 40

        addr = text[start:end]
        addr = addr.replace("\n", " ")

        if "Certificate" not in addr and "Stamp" not in addr:
            result["address"] = addr.strip()
    '''
    # ---------------------------
# ADDRESS (search near end)
# ---------------------------

        # ADDRESS
    addr_match = re.search(
        r'(?:residing at|resident of)\s+(No\.?\s*[^.\n]{10,120})',
        text, re.I
    )
    if addr_match:
        result["address"] = re.sub(r'\s+', ' ', addr_match.group(1)).strip()
        # ---------------------------
    # CONSTITUENCY
    # ---------------------------
    '''
    m = re.search(
    r'from\s+(\d+)\s+([A-Za-z\s]+?)\s+constituency',
    text,
    re.I
)

    if m:
        result["constituency_number"] = m.group(1)
        result["constituency_name"] = m.group(2).strip()
    '''
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

        
        
    # FATHER'S NAME
    father_match = re.search(
        r'[Ss]/[Oo]\.?\s+([A-Z][a-zA-Z\s\.]{3,40})',
        text
    )
    if not father_match:
        father_match = re.search(
            r'[Ss]on\s+of\s+(?:Mr\.?\s*)?([A-Z][a-zA-Z\s\.]{3,40})',
            text, re.I
        )
    if father_match:
        result["fathers_name"] = father_match.group(1).strip().split("\n")[0]
    return result