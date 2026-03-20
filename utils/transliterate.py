# utils/transliterate.py
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


def tamil_to_english(text):
    try:
        result = transliterate(text, sanscript.TAMIL, sanscript.ITRANS)
        return result
    except:
        return text