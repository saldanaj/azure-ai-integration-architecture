import base64
import unittest
from importlib import util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXTRACTOR_MODULE = BASE_DIR / "services" / "fhir-listener" / "extractor.py"

spec = util.spec_from_file_location("extractor", EXTRACTOR_MODULE)
assert spec and spec.loader
module = util.module_from_spec(spec)
spec.loader.exec_module(module)
extract_followups = module.extract_followups

NOTE_TEXT = (
    "Patient: Sarah Connor (P123)\n"
    "Encounter: E456 | Discharge Date: 2024-02-12\n"
    "Primary Diagnosis: Acute decompensated heart failure.\n\n"
    "Follow-up Instructions:\n"
    "1. Labs: Obtain a basic metabolic panel in 3 days to monitor renal function and potassium after starting lisinopril.\n"
    "2. Visit: Schedule a cardiology follow-up within 7 days to assess volume status and titrate meds.\n"
    "3. Medication: Nursing team to call the patient in 48 hours to reinforce low-sodium diet and confirm medication adherence.\n"
)

DOCUMENT = {
    "resourceType": "DocumentReference",
    "id": "D789",
    "content": [
        {
            "attachment": {
                "contentType": "text/plain",
                "data": base64.b64encode(NOTE_TEXT.encode("utf-8")).decode("ascii"),
            }
        }
    ],
}


class ExtractorTests(unittest.TestCase):
    def test_followups_match_expected(self) -> None:
        followups = extract_followups(DOCUMENT, patient_id="P123", encounter_id="E456")
        self.assertEqual(len(followups), 3)
        self.assertEqual(followups[0]["category"], "lab")
        self.assertEqual(followups[0]["dueDate"], "2024-02-15")
        self.assertEqual(followups[1]["category"], "visit")
        self.assertEqual(followups[1]["dueDate"], "2024-02-19")
        self.assertEqual(followups[2]["category"], "med")
        self.assertEqual(followups[2]["dueDate"], "2024-02-14")


if __name__ == "__main__":
    unittest.main()
