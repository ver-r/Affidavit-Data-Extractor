# extractor/spacy_ner.py

import spacy

nlp = spacy.load("en_core_web_sm")


def extract_entities(text):

    doc = nlp(text[:3000])

    result = {}

    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    locations = [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")]

    if persons:
        result["full_name"] = persons[0]

    if len(persons) > 1:
        result["fathers_name"] = persons[1]

    if locations:
        result["address"] = locations[0]

    return result