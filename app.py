# api/app.py
from flask import Flask, request, jsonify
import tempfile, os
from main import process_pdf
from database.schema import build_record
from database.mysql_handler import insert_extraction
from utils.logger import get_logger

app = Flask(__name__)
log = get_logger()

@app.route("/extract", methods=["POST"])
def extract():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files accepted"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        extracted, pan_result = process_pdf(tmp_path)
        if not pan_result.get("pan_number"):
            log.warning(f"No PAN found in uploaded file: {file.filename}")
            return jsonify({"error": "No PAN found, record not saved"}), 422

        record = build_record(extracted, pan_result, file.filename)
        insert_extraction(record)
        log.info(f"API processed: {file.filename}")
        return jsonify(record), 200

    except Exception as e:
        log.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    app.run(debug=True, port=5000)