# extractor/ocr_extractor.py
"""
OCR-based extraction using pypdfium2 (no poppler) + Tesseract.
Uses rule-based NER on OCR output to extract named entities.
Tamil Unicode output is transliterated to English before storing.
"""

import re
import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageEnhance


# ── Tamil → English transliteration ───────────────────────────────────────

def transliterate_tamil(text: str) -> str:
    """
    Convert Tamil Unicode text to English romanization.
    Tries indic_transliteration library first; falls back to built-in map.
    Returns input unchanged if it contains no Tamil Unicode.
    """
    if not text:
        return text
    if not any('\u0B80' <= c <= '\u0BFF' for c in text):
        return text  # already English/ASCII

    # Try the proper library first (pip install indic-transliteration)
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        result = transliterate(text, sanscript.TAMIL, sanscript.HK)
        return ' '.join(w.capitalize() for w in result.split() if w)
    except ImportError:
        pass

    # Built-in fallback: handles consonant + vowel-sign combinations
    CONSONANTS = {
        'க': 'k',  'ங': 'ng', 'ச': 'ch', 'ஞ': 'nj', 'ட': 'd',
        'ண': 'n',  'த': 'th', 'ந': 'n',  'ப': 'p',  'ம': 'm',
        'ய': 'y',  'ர': 'r',  'ல': 'l',  'வ': 'v',  'ழ': 'zh',
        'ள': 'l',  'ற': 'r',  'ன': 'n',  'ஜ': 'j',  'ஷ': 'sh',
        'ஸ': 's',  'ஹ': 'h',
    }
    VOWELS = {
        'அ': 'a',  'ஆ': 'aa', 'இ': 'i',  'ஈ': 'ee', 'உ': 'u',
        'ஊ': 'oo', 'எ': 'e',  'ஏ': 'ae', 'ஐ': 'ai', 'ஒ': 'o',
        'ஓ': 'oo', 'ஔ': 'au',
    }
    VOWEL_SIGNS = {
        'ா': 'aa', 'ி': 'i',  'ீ': 'ee', 'ு': 'u',  'ூ': 'oo',
        'ெ': 'e',  'ே': 'ae', 'ை': 'ai', 'ொ': 'o',  'ோ': 'oo',
        'ௌ': 'au', '்': '',   # pulli = no vowel after consonant
    }
    SKIP = {'\u200c', '\u200b', '\u200d', '\u0bcd'}

    result = []
    chars = list(text)
    i = 0
    while i < len(chars):
        c = chars[i]
        if c in SKIP:
            i += 1
            continue
        if c in VOWELS:
            result.append(VOWELS[c])
            i += 1
        elif c in CONSONANTS:
            base = CONSONANTS[c]
            i += 1
            if i < len(chars) and chars[i] in VOWEL_SIGNS:
                sign = VOWEL_SIGNS[chars[i]]
                result.append(base if sign == '' else base + sign)
                i += 1
            elif i < len(chars) and chars[i] in SKIP:
                result.append(base)
                i += 1
            else:
                result.append(base + 'a')
        elif '\u0B80' <= c <= '\u0BFF':
            i += 1
        else:
            result.append(c)
            i += 1

    return ' '.join(w.capitalize() for w in ''.join(result).split() if w)


def _has_tamil(text: str) -> bool:
    return any('\u0B80' <= c <= '\u0BFF' for c in text)


# ── Rendering ──────────────────────────────────────────────────────────────

def _render_page(pdf_path: str, page_num: int, dpi: int = 200) -> Image.Image:
    doc = pdfium.PdfDocument(pdf_path)
    try:
        bitmap = doc[page_num - 1].render(scale=dpi / 72)
        img = bitmap.to_pil().convert('L')
        return ImageEnhance.Contrast(img).enhance(2.0)
    finally:
        doc.close()


def _ocr(img: Image.Image, lang: str = 'eng+tam') -> str:
    try:
        return pytesseract.image_to_string(img, lang=lang, config='--psm 6 --oem 3')
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(img, lang='eng', config='--psm 6 --oem 3')


def get_page_count(pdf_path: str) -> int:
    doc = pdfium.PdfDocument(pdf_path)
    n = len(doc)
    doc.close()
    return n


def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


# ── Tamil Unicode NER (from Tamil OCR output) ─────────────────────────────

def _ner_from_tamil(text: str) -> dict:
    """
    Named Entity Recognition on Tamil Unicode text.
    Extracts: PERSON (father), AGE, CONSTITUENCY.
    All Tamil output is transliterated to English before returning.
    """
    result = {}

    # PERSON: "FATHER_NAME என்பவரின்" = "son/daughter of FATHER_NAME"
    m = re.search(r'([^\s,\.।\n]{2,30})\s+என்பவரின்', text)
    if m:
        father_tamil = _clean(m.group(1))
        result['fathers_name'] = transliterate_tamil(father_tamil)

    # AGE: "N வயதுடைய" = "N years old"
    m = re.search(r'(\d{2})\s+வயதுடைய', text)
    if m:
        age = int(m.group(1))
        if 18 <= age <= 100:
            result['age'] = age

    # CONSTITUENCY NUMBER: "வரிசை எண்.N"
    m = re.search(r'வரிசை\s+எண்[\.:\s]+(\d+)', text)
    if m:
        result['constituency_number'] = m.group(1)

    # CONSTITUENCY NAME: "N, PLACE தொகுதி"
    m = re.search(r'\d+\s*,\s*([^\n,]{3,30}?)\s+தொகுதி', text)
    if m:
        name_tamil = _clean(m.group(1))
        result['constituency_name'] = transliterate_tamil(name_tamil)

    # ADDRESS: paguti B has "முழு அஞ்சல் முகவரி FULL_ADDRESS-PINCODE"
    m = re.search(r'முழு\s+அஞ்சல்\s+முகவரி\s+(.*?\d{6})', text, re.S)
    if m:
        addr_raw = _clean(m.group(1).replace('\n', ' '))
        result['address'] = transliterate_tamil(addr_raw)

    return result


# ── English NER on notarial certificate ───────────────────────────────────

def _ner_from_notarial(text: str) -> dict:
    """
    Rule-based NER on the English notarial certificate.
    Extracts PERSON (name, father) and GPE/LOC (address, constituency).
    """
    result = {}

    # PERSON: "certify that NAME [son/wife/daughter] of PARENT"
    m = re.search(
        r'certif[yi]+\s+that\s+([A-Z][A-Z\s\.]+?)\s*[,.]?\s*'
        r'(?:son|wife|daughter)\s+of\s+(?:Mr\.\s*|Mrs\.\s*)?([A-Z][a-zA-Z\s\.]+?)'
        r'(?=\s+residing|\s+[a-z]{3,}\s+at|[,\.\n\d])',
        text, re.I
    )
    if m:
        result['full_name'] = _clean(m.group(1))
        result['fathers_name'] = _clean(m.group(2))

    # LOC: "residing at ADDRESS PINCODE" — allow spaced pincode "605 007"
    m = re.search(
        r'residing at\s+((?:No\.?\s*)?\w.*?\d{3}\s?\d{3})',
        text, re.I | re.S
    )
    if not m:
        m = re.search(r'resident of\s+(.*?\d{3}\s?\d{3})', text, re.I | re.S)
    if m:
        addr = m.group(1).replace('\n', ' ')
        addr = re.sub(r'\s*[—–]\s*(\d)', r' - \1', addr)
        result['address'] = _clean(addr)

    # GPE: constituency from "Election from NAME Constituency"
    m = re.search(
        r'(?:Election\s+from|from\s+)([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+Constituency',
        text, re.I
    )
    if m:
        result['constituency_name'] = _clean(m.group(1))

    # Optional spaCy ML-NER enhancement
    try:
        import spacy
        try:
            nlp = spacy.load('en_core_web_sm')
        except OSError:
            nlp = None
        if nlp:
            doc_nlp = nlp(text[:3000])
            persons = [e.text for e in doc_nlp.ents if e.label_ == 'PERSON']
            locs    = [e.text for e in doc_nlp.ents if e.label_ in ('GPE', 'LOC')]
            print(f"    [spaCy NER] PERSON={persons[:3]}, GPE/LOC={locs[:3]}")
            if not result.get('full_name') and persons:
                result['full_name'] = _clean(persons[0])
            if not result.get('fathers_name') and len(persons) > 1:
                result['fathers_name'] = _clean(persons[1])
    except ImportError:
        pass

    return result


# ── Structured extraction from page 2 (contact info) ──────────────────────

def _extract_from_content_page(text: str) -> dict:
    """Extract mobile, age, email, constituency from page 2 OCR (eng+tam)."""
    result = {}

    # MOBILE: WhatsApp line is most reliably OCR'd
    wa = re.search(r'[Ww]hats?\s*[Aa]pp\s+([\d\s]{10,12})', text)
    if wa:
        digits = re.sub(r'\D', '', wa.group(1))
        if len(digits) == 10 and digits[0] in '6789':
            result['mobile'] = digits

    if not result.get('mobile'):
        m3 = re.search(r'\(3\)(.*?)(?:\(4\)|\Z)', text, re.S)
        area = m3.group(1) if m3 else text[:2000]
        mobiles = re.findall(r'\b([6-9]\d{9})\b', area)
        if mobiles:
            result['mobile'] = mobiles[0]

    if not result.get('mobile'):
        mobiles = re.findall(r'\b([6-9]\d{9})\b', text)
        if mobiles:
            result['mobile'] = mobiles[0]

    # AGE: English
    m = re.search(r'aged\s+(\d{1,3})\s+years', text, re.I)
    if m:
        age = int(m.group(1))
        if 18 <= age <= 100:
            result['age'] = age

    # AGE: Tamil Unicode
    if not result.get('age'):
        m = re.search(r'(\d{2})\s+வயதுடைய', text)
        if m:
            age = int(m.group(1))
            if 18 <= age <= 100:
                result['age'] = age

    # AGE: Tamil transliterated OCR "N auXXXLw"
    if not result.get('age'):
        m = re.search(r'\b(\d{2})\s+(?:au|aw|ow|ug|um)[a-zA-Z]+', text, re.I)
        if m:
            age = int(m.group(1))
            if 18 <= age <= 100:
                result['age'] = age

    # EMAIL: must start with letter, proper domain
    emails = re.findall(
        r'[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', text
    )
    for email in emails:
        local, domain = email.split('@', 1)
        if (local[0].isalpha() and len(local) >= 4
                and len(domain) > 5 and '.' in domain
                and re.match(r'^[A-Za-z0-9._%+\-]+$', local)):
            result['email'] = email
            break

    # CONSTITUENCY NUMBER
    m = re.search(r'வரிசை\s+எண்[\.:\s]+(\d+)', text)
    if m:
        result['constituency_number'] = m.group(1)
    if not result.get('constituency_number'):
        m = re.search(r'(?:crovet|croir|croit)\s*[\.:]?\s*(\d{2,4})', text, re.I)
        if m:
            result['constituency_number'] = m.group(1)
    if not result.get('constituency_number'):
        m = re.search(r'from\s+(\d+)[,\s]+[A-Za-z]', text, re.I)
        if m:
            result['constituency_number'] = m.group(1)

    return result


# ── Main function ──────────────────────────────────────────────────────────

def extract_via_ocr(pdf_path: str, existing: dict) -> dict:
    """
    Fill missing fields via OCR + NER. Never overwrites existing values.

    Steps:
      1. Tamil OCR (lang='tam') on page 2  → father/age/constituency in Tamil Unicode
                                             → transliterated to English
      2. eng+tam OCR on page 2             → mobile/email (mixed content)
      3. eng+tam OCR on last 2 pages       → English NER on notarial cert
      4. paguti B scan                     → constituency number fallback
    """
    total = get_page_count(pdf_path)
    result = existing.copy()

    need_contact     = any(not result.get(f) for f in ['mobile', 'age', 'email'])
    need_name        = any(not result.get(f) for f in ['full_name', 'fathers_name', 'address'])
    need_constituency = not result.get('constituency_number')

    # ── Step 1: Tamil OCR on page 2 → Tamil NER ──────────────────────────
    if (need_name or need_constituency) and total >= 2:
        print("  [OCR Tamil] page 2 → father/age/constituency")
        img = _render_page(pdf_path, 2, dpi=250)
        text_tamil = _ocr(img, lang='tam')

        if _has_tamil(text_tamil):
            tamil_fields = _ner_from_tamil(text_tamil)
            for k, v in tamil_fields.items():
                if v and not result.get(k):
                    result[k] = v
        else:
            print("    (Tamil tessdata unavailable - skipping Tamil NER)")

    # ── Step 2: Tamil OCR on paguti B → address + constituency ───────────
    # Paguti B is typically at total-2 to total-3 pages from end
    if not result.get('address') or need_constituency:
        for pg_offset in [2, 3, 4]:
            pg = total - pg_offset
            if pg >= 1:
                img = _render_page(pdf_path, pg, dpi=200)
                text_summary = _ocr(img, lang='tam')
                if _has_tamil(text_summary):
                    summary_fields = _ner_from_tamil(text_summary)
                    if summary_fields.get('address') and not result.get('address'):
                        result['address'] = summary_fields['address']
                    if summary_fields.get('constituency_number') and not result.get('constituency_number'):
                        result['constituency_number'] = summary_fields['constituency_number']
                    if summary_fields.get('constituency_name') and not result.get('constituency_name'):
                        result['constituency_name'] = summary_fields['constituency_name']
                    if result.get('address'):  # found it, stop searching
                        break

    # ── Step 3: eng+tam OCR on page 2 → mobile/email/constituency ────────
    if need_contact or need_constituency:
        print("  [OCR eng+tam] page 2 → mobile/age/email/constituency")
        img = _render_page(pdf_path, 2, dpi=200)
        text_mixed = _ocr(img, lang='eng+tam')
        contact = _extract_from_content_page(text_mixed)
        for k, v in contact.items():
            if v and not result.get(k):
                result[k] = v

    # ── Step 4: English NER on last pages (notarial cert) ────────────────
    still_need = any(not result.get(f) for f in ['full_name', 'fathers_name', 'address'])
    if still_need:
        print("  [OCR+NER] last pages → notarial cert (English NER)")
        notarial_text = ""
        for pg in range(max(1, total - 1), total + 1):
            img = _render_page(pdf_path, pg, dpi=200)
            notarial_text += _ocr(img, lang='eng+tam') + "\n"
        ner = _ner_from_notarial(notarial_text)
        for k, v in ner.items():
            if v and not result.get(k):
                result[k] = v

    # ── Step 5: paguti B eng+tam fallback for constituency number ─────────
    if not result.get('constituency_number'):
        img = _render_page(pdf_path, max(1, total - 2), dpi=200)
        summary = _ocr(img, lang='eng+tam')
        m = re.search(r'vor[sS]B\w*\s+(\d{2,3})', summary)
        if m:
            result['constituency_number'] = m.group(1)

    return result