"""Generates the 4 sample document images + their cached extraction JSON.

No real scanned forms exist for this project, so these are programmatically
drawn "form-like" images (label: value pairs, a table for the tabular docs).
That's fine for their purpose: exercising the full upload -> extract -> review
-> commit pipeline in VISION_PROVIDER=fixture mode (§6.1's "Try a sample"
button), not testing OCR accuracy against real handwriting.

Bounding boxes are NOT guessed — each value's pixel box is captured at draw
time from PIL's own layout, then normalized to 0-1, so the review UI's
focus-a-field-draws-its-bbox actually points at the right spot on these
samples.

Run manually to regenerate: `python fixtures/generate_fixtures.py`. Output is
committed (images + JSON), so this script doesn't run at app startup or in
tests — it's provenance, not a build step.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).resolve().parent
IMAGES_DIR = FIXTURES_DIR / "samples"
RESPONSES_DIR = FIXTURES_DIR / "responses"

WIDTH, HEIGHT = 900, 700
LABEL_FONT_SIZE = 22
VALUE_FONT_SIZE = 26
TITLE_FONT_SIZE = 34


def _fonts() -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    return {
        "title": ImageFont.load_default(size=TITLE_FONT_SIZE),
        "label": ImageFont.load_default(size=LABEL_FONT_SIZE),
        "value": ImageFont.load_default(size=VALUE_FONT_SIZE),
    }


class FormBuilder:
    """Draws label/value rows on a plain form background and records each
    value's normalized bbox as it's placed."""

    def __init__(self, title: str) -> None:
        self.img = Image.new("RGB", (WIDTH, HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.img)
        self.fonts = _fonts()
        self.y = 40
        self.fields: list[dict] = []
        self.draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], outline="black", width=3)
        self.draw.text((40, self.y), title, font=self.fonts["title"], fill="black")
        self.y += 70
        self.draw.line([(30, self.y), (WIDTH - 30, self.y)], fill="black", width=2)
        self.y += 30

    def row(self, label: str, value: str, name: str, confidence: float) -> None:
        self.draw.text((50, self.y), f"{label}:", font=self.fonts["label"], fill="black")
        value_x = 320
        self.draw.text((value_x, self.y - 2), value, font=self.fonts["value"], fill=(20, 20, 120))
        bbox = self.draw.textbbox((value_x, self.y - 2), value, font=self.fonts["value"])
        self.fields.append(
            {
                "name": name,
                "value": value,
                "confidence": confidence,
                "bbox": [
                    round(bbox[0] / WIDTH, 4),
                    round(bbox[1] / HEIGHT, 4),
                    round(bbox[2] / WIDTH, 4),
                    round(bbox[3] / HEIGHT, 4),
                ],
            }
        )
        self.y += 55

    def table(
        self, headers: list[str], rows: list[list[str]], col_x: list[int]
    ) -> list[list[list[float]]]:
        header_y = self.y
        for text, x in zip(headers, col_x, strict=True):
            self.draw.text((x, header_y), text, font=self.fonts["label"], fill="black")
        self.y += 40
        self.draw.line([(30, self.y), (WIDTH - 30, self.y)], fill="black", width=1)
        self.y += 15

        row_bboxes = []
        for row in rows:
            cell_bboxes = []
            for text, x in zip(row, col_x, strict=True):
                self.draw.text((x, self.y), text, font=self.fonts["value"], fill=(20, 20, 120))
                bbox = self.draw.textbbox((x, self.y), text, font=self.fonts["value"])
                cell_bboxes.append(
                    [
                        round(bbox[0] / WIDTH, 4),
                        round(bbox[1] / HEIGHT, 4),
                        round(bbox[2] / WIDTH, 4),
                        round(bbox[3] / HEIGHT, 4),
                    ]
                )
            row_bboxes.append(cell_bboxes)
            self.y += 45
        return row_bboxes

    def save_and_write_fixture(
        self,
        filename: str,
        doc_type: str,
        doc_type_confidence: float,
        rows: list[dict],
        warnings: list[str],
    ) -> None:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

        image_path = IMAGES_DIR / filename
        self.img.save(image_path, "JPEG", quality=92)

        image_bytes = image_path.read_bytes()
        key = hashlib.sha256(image_bytes).hexdigest()[:16]

        payload = {
            "doc_type": doc_type,
            "doc_type_confidence": doc_type_confidence,
            "fields": self.fields,
            "rows": rows,
            "warnings": warnings,
        }
        (RESPONSES_DIR / f"{key}.json").write_text(json.dumps(payload, indent=2))
        print(f"{filename} -> {key}.json ({len(self.fields)} fields, {len(rows)} rows)")


def build_admission_form() -> None:
    f = FormBuilder("ADMISSION FORM")
    f.row("Student Name", "Ananya Verma", "student_name", 0.96)
    f.row("Admission No", "ADM09051", "admission_no", 0.95)
    f.row("Class", "9-A", "class_label", 0.93)
    # Existing 9-A students occupy roll 1-50 (seed.py) -- 51 is the next slot,
    # not a collision.
    f.row("Roll No", "51", "roll_no", 0.9)
    f.row("Guardian Name", "Rajesh Verma", "guardian_name", 0.88)
    # Deliberately low confidence -- the smudged-phone-number demo moment
    # (amber field, corrected in the review UI before commit).
    f.row("Guardian Phone", "98123456xx", "guardian_phone", 0.6)
    f.save_and_write_fixture("admission_form.jpg", "admission_form", 0.97, [], [])


def build_attendance_sheet() -> None:
    f = FormBuilder("ATTENDANCE SHEET")
    f.row("Class", "8-A", "class_label", 0.92)
    f.row("Date", "2026-08-03", "date", 0.9)
    f.y += 10
    col_x = [50, 200, 550]
    row_bboxes = f.table(
        ["Roll No", "Name", "Status"],
        [
            ["1", "Aadhya Kumar", "Present"],
            ["2", "Arjun Mehta", "Absent"],
            ["3", "Diya Iyer", "Present"],
        ],
        col_x,
    )
    rows = [
        {
            "roll_no": "1",
            "name": "Aadhya Kumar",
            "status": "present",
            "confidence": 0.93,
            "bbox": row_bboxes[0],
        },
        {
            "roll_no": "2",
            "name": "Arjun Mehta",
            "status": "absent",
            "confidence": 0.91,
            "bbox": row_bboxes[1],
        },
        # Deliberately low confidence on one row -- another amber-field case,
        # this time inside a table row rather than a top-level field.
        {
            "roll_no": "3",
            "name": "Diya Iyer",
            "status": "present",
            "confidence": 0.7,
            "bbox": row_bboxes[2],
        },
    ]
    f.save_and_write_fixture("attendance_sheet.jpg", "attendance_sheet", 0.94, rows, [])


def build_marks_sheet() -> None:
    f = FormBuilder("MARKS SHEET")
    f.row("Class", "7-B", "class_label", 0.88)
    f.row("Subject", "Mathematics", "subject", 0.85)
    f.row("Term", "Term 1", "term", 0.8)
    f.y += 10
    col_x = [50, 200, 550]
    row_bboxes = f.table(
        ["Roll No", "Name", "Marks /100"],
        [["1", "Kabir Singh", "87"], ["2", "Meera Rao", "92"]],
        col_x,
    )
    rows = [
        {
            "roll_no": "1",
            "name": "Kabir Singh",
            "marks": "87",
            "confidence": 0.9,
            "bbox": row_bboxes[0],
        },
        {
            "roll_no": "2",
            "name": "Meera Rao",
            "marks": "92",
            "confidence": 0.85,
            "bbox": row_bboxes[1],
        },
    ]
    warnings = [
        "Marks are extracted for review only -- Shaala OS does not store grades "
        "or generate report cards (deliberately out of scope, see README roadmap)."
    ]
    f.save_and_write_fixture("marks_sheet.jpg", "marks_sheet", 0.9, rows, warnings)


def build_leave_application() -> None:
    f = FormBuilder("LEAVE APPLICATION")
    f.row("Teacher Name", "Priya Nair", "teacher_name", 0.93)
    f.row("Employee Code", "T005", "teacher_code", 0.91)
    f.row("Date of Leave", "2026-08-10", "leave_date", 0.89)
    f.row("Reason", "Medical - fever", "reason", 0.75)
    f.save_and_write_fixture("leave_application.jpg", "leave_application", 0.95, [], [])


if __name__ == "__main__":
    build_admission_form()
    build_attendance_sheet()
    build_marks_sheet()
    build_leave_application()
