from transformers import pipeline

try:
    ner_pipeline = pipeline("ner", model="ai4bharat/IndicNER", aggregation_strategy="simple")
except Exception as e:
    print(f"[ner_extractor] WARNING: NER model failed to load: {e}")
    ner_pipeline = None
def run_ner(text_blocks):
    if ner_pipeline is None:
        return {"full_name": None, "fathers_name": None, "address": None}

    text = "\n".join(text_blocks)

    entities = ner_pipeline(text)

    result = {
        "full_name": None,
        "fathers_name": None,
        "address": None
    }

    persons = []
    locations = []

    for ent in entities:

        if ent["entity_group"] == "PER":
            persons.append(ent["word"])

        if ent["entity_group"] == "LOC":
            locations.append(ent["word"])

    if persons:
        result["full_name"] = persons[0]

    if len(persons) > 1:
        result["fathers_name"] = persons[1]

    if locations:
        result["address"] = " ".join(locations[:4])

    return result