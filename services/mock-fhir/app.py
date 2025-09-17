from base64 import b64encode
from flask import Flask, jsonify

app = Flask(__name__)

NOTE_BY_DOCUMENT = {
    "D789": """Patient: Sarah Connor (P123)\nEncounter: E456 | Discharge Date: 2024-02-12\nPrimary Diagnosis: Acute decompensated heart failure.\nHospital Course: Improved with IV diuretics, transitioned to oral medications.\n\nFollow-up Instructions:\n1. Labs: Obtain a basic metabolic panel in 3 days to monitor renal function and potassium after starting lisinopril.\n2. Visit: Schedule a cardiology follow-up within 7 days to assess volume status and titrate meds.\n3. Medication: Nursing team to call the patient in 48 hours to reinforce low-sodium diet and confirm medication adherence.\n\nDischarge Medications: Furosemide, Lisinopril, Spironolactone.\nMRN: 555443\n""",
}


@app.get("/fhir/DocumentReference/<doc_id>")
def get_doc(doc_id: str):
    note = NOTE_BY_DOCUMENT.get(doc_id, "Synthetic discharge note not found.")
    encoded = b64encode(note.encode("utf-8")).decode("ascii")
    return jsonify(
        {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "description": "Synthetic discharge summary",
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "data": encoded,
                    }
                }
            ],
        }
    )


@app.get("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
