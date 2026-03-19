# extractor/pdf_extractor.py
"""
Direct PDF text extraction using pdfplumber.
Handles: Puducherry e-Stamp, Tamil Nadu paper stamp, mixed-format affidavits.
"""

import re
import pdfplumber


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fix_pan_chars(text: str) -> str:
    """Fix font-encoding: O->0, l->1, S->5 in PAN digit positions."""
    def _fix(m):
        chars = list(m.group(0))
        for i in range(5, 9):
            chars[i] = (chars[i]
                        .replace('O', '0').replace('o', '0')
                        .replace('l', '1').replace('I', '1')
                        .replace('S', '5'))
        return ''.join(chars)
    return re.sub(r'[A-Z]{5}[A-Z0-9OolIS]{4}[A-Z]', _fix, text)


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def extract_text_from_pdf(pdf_path: str):
    """Returns (full_text, pages_list)."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    pages = [_fix_pan_chars(p) for p in pages]
    return "\n".join(pages), pages


# ---------------------------------------------------------------------------
# Name + Father
# ---------------------------------------------------------------------------

def _extract_name_and_father(full_text: str):
    """Try all known patterns. Returns (name, father)."""

    # 1. Notarial cert: "certify that NAME son/wife/daughter of PARENT"
    m = re.search(
        r'certif[yi]+\s+that\s+([A-Z][A-Z\s\.]+?)\s*[,.]?\s*'
        r'(?:son|wife|daughter)\s+of\s+(?:Mr\.\s*|Mrs\.\s*)?([A-Z][a-zA-Z\s]+?)[,\.]',
        full_text, re.I
    )
    if m:
        return _clean(m.group(1)), _clean(m.group(2))

    # 2. Standard: "NAME S/o. PARENT, aged"
    m = re.search(
        r'\b([A-Z][a-zA-Z\s\.]{2,40}?),?\s+[SsWwDd]/[Oo]\.?\s+([A-Z][a-zA-Z\s\.]{2,40}?),?\s+aged',
        full_text
    )
    if m:
        return _clean(m.group(1)), _clean(m.group(2))

    # 3. E-stamp header: "Purchased by" or "First Party"
    name = None
    for pat in [
        r'Purchased\s+by\s*:?\s*([A-Z][A-Z\s\.]+?)(?:\n|Article)',
        r'First\s+Party\s*:?\s*([A-Z][A-Z\s\.]+?)(?:\n|Second)',
    ]:
        m = re.search(pat, full_text, re.I)
        if m:
            candidate = _clean(m.group(1))
            words = candidate.split()
            if 1 <= len(words) <= 6 and len(candidate) <= 45:
                name = candidate
                break

    if name:
        father = _extract_father_near(full_text, name)
        return name, father

    return None, None


def _extract_father_near(full_text: str, name: str) -> str | None:
    """Find father's name near the candidate name."""
    # S/o or W/o after name
    escaped = re.escape(name[:12])
    m = re.search(
        rf'{escaped}.*?[SsWwDd]/[Oo]\.?\s*([A-Z][a-zA-Z\s\.]+?)[,\n\d]',
        full_text, re.S
    )
    if m:
        f = _clean(m.group(1))
        if 3 < len(f) < 50:
            return f

    # Tamil pattern: "FATHER என்பவரின்" = son/daughter of FATHER
    m = re.search(r'([A-Z][a-zA-Z\s\.]{3,30}?)\s+என்பவரின்', full_text)
    if m:
        return _clean(m.group(1))

    return None


# ---------------------------------------------------------------------------
# Age
# ---------------------------------------------------------------------------

def _extract_age(full_text: str):
    patterns = [
        r'aged\s+(\d{1,3})\s+years',
        r'\b(\d{1,3})\s+வயதுடைய',   # Tamil: "46 வயதுடைய"
        r'வயதுடைய\s+\S+\s+(\d{1,3})',
    ]
    # Also: Tamil Nadu format embeds age next to pincode on a key line
    # e.g. "45 qglriGorfl-605007" — age number before city garble
    m = re.search(r'\b(\d{2})\s+[a-zA-Z\u0B80-\u0BFF]{4,}.*?\d{6}', full_text)
    if m:
        age = int(m.group(1))
        if 18 <= age <= 100:
            return age

    for pat in patterns:
        m = re.search(pat, full_text, re.I)
        if m:
            age = int(m.group(1))
            if 18 <= age <= 100:
                return age
    return None


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

def _extract_address(full_text: str):
    for pat in [
        r'resident of\s+(.*?\d{3}\s*\d{3})',
        r'residing at\s+(?:No\.\s*)?(.*?\d{3}\s*\d{3})',
    ]:
        m = re.search(pat, full_text, re.I | re.S)
        if m:
            addr = _clean(m.group(1).replace('\n', ' '))
            if len(addr) > 15:
                return addr
    return None


# ---------------------------------------------------------------------------
# PAN
# ---------------------------------------------------------------------------

def _extract_pans(full_text: str) -> list:
    FALSE_POSITIVES = {'COMMI5510N', 'ELECCOMM1N', 'COMMISS10N'}
    pans = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', full_text)
    seen, result = set(), []
    for p in pans:
        if p not in FALSE_POSITIVES and p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Mobile
# ---------------------------------------------------------------------------

def _extract_mobile(full_text: str):
    """
    Affidavit item (3) is always the candidate's phone number.
    We search for a 10-digit Indian mobile in the first ~5000 chars
    (the contact section), returning the FIRST one found.
    The WhatsApp/social media numbers come AFTER the primary number
    so taking the first is correct.
    """
    # Search in first portion of text (contact info is always early)
    search_area = full_text[:5000]
    mobiles = re.findall(r'\b([6-9]\d{9})\b', search_area)
    if mobiles:
        return mobiles[0]
    # Fallback
    m = re.search(r'\b([6-9]\d{9})\b', full_text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _extract_email(full_text: str):
    emails = re.findall(
        r'[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',
        full_text
    )
    for email in emails:
        local = email.split('@')[0]
        domain = email.split('@')[1]
        # Must look like a real email: 3+ chars local, recognizable domain
        if (len(local) >= 3
                and re.match(r'^[A-Za-z0-9._%+\-]+$', local)
                and re.match(r'^[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$', domain)
                and len(domain) > 4):
            return email
    return None


# ---------------------------------------------------------------------------
# Constituency
# ---------------------------------------------------------------------------

def _extract_constituency(full_text: str):
    name = None
    number = None

    # Name: "Election from NAME Constituency"
    m = re.search(
        r'(?:Election\s+from|from\s+)([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+Constituency',
        full_text, re.I
    )
    if m:
        name = _clean(m.group(1))

    # Number: "from 18, NAME" 
    m = re.search(r'from\s+(\d+)[,\s]+[A-Za-z]', full_text, re.I)
    if m:
        number = m.group(1)

    if not number:
        # Tamil Nadu: "வரிசை எண்.711" or just after Constituency keyword
        m = re.search(r'வரிசை\s+எண்[\.:]?\s*(\d+)', full_text)
        if m:
            number = m.group(1)

    if not number:
        m = re.search(r'Constituency\s*[,No\.]*\s*(\d+)', full_text, re.I)
        if m:
            number = m.group(1)

    # Also look for constituency name in Tamil Nadu format:
    # the Tamil affidavit intro mentions constituency in Tamil (mostly garbled)
    # but item (2) says constituency name explicitly
    if not name:
        # Pattern: "009 மாதவரம் தமிழ்நாடு" - Tamil Nadu constituency
        # Or "Ariankuppam" appears in address which IS the constituency
        # Check if address contains a known pattern
        m = re.search(r'\b(Ariankuppam|Mudaliarpet|Manaveli|Villiyanur|Oulgaret)\b', full_text, re.I)
        if m:
            name = m.group(1)

    return name, number


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_all_fields(pdf_path: str) -> dict:
    """Extract all fields. Returns flat dict; missing fields are None."""
    full_text, pages = extract_text_from_pdf(pdf_path)
    result = {}

    name, father = _extract_name_and_father(full_text)
    if name:
        result["full_name"] = name
    if father:
        result["fathers_name"] = father

    age = _extract_age(full_text)
    if age:
        result["age"] = age

    addr = _extract_address(full_text)
    if addr:
        result["address"] = addr

    pans = _extract_pans(full_text)
    if pans:
        result["pan_number"] = pans[0]

    mob = _extract_mobile(full_text)
    if mob:
        result["mobile"] = mob

    email = _extract_email(full_text)
    if email:
        result["email"] = email

    cons_name, cons_number = _extract_constituency(full_text)
    if cons_name:
        result["constituency_name"] = cons_name
    if cons_number:
        result["constituency_number"] = cons_number

    return result


if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pdf_extractor.py <path_to_pdf>")
        sys.exit(1)
    print(json.dumps(extract_all_fields(path), indent=2))