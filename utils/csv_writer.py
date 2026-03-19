# utils/csv_writer.py
import csv
import os
from datetime import datetime

FIELDS = [
    "source_file", "full_name", "fathers_name", "age",
    "address", "mobile", "constituency_number", "constituency_name",
    "pan_number", "pan_valid", "pan_confidence", "extraction_status"
]

def write_csv(records: list, output_dir: str = "."):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"extracted_{timestamp}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"[csv_writer] Saved: {path}")
    return path