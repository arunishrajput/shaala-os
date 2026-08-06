"""Phase 3 gate (PROMPT.md §9): with VISION_PROVIDER=fixture and the network
disabled, a sample admission form becomes a student record in under 15
seconds. Plus coverage for confidence routing and all 4 doc-type commit paths.
"""

import time
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import seed as seed_module
from app.db.models import (
    AttendanceRecord,
    Document,
    DocumentStatus,
    ExtractedField,
    Student,
    TeacherAbsence,
)
from app.db.session import SessionLocal
from app.services.documents import CommitError, commit_document, process_upload

FIXTURES_SAMPLES = Path(__file__).resolve().parents[1] / "fixtures" / "samples"


@pytest.fixture(scope="module")
def db():
    seed_module.main()  # documents.py's commit handlers look up real seeded data
    session = SessionLocal()
    yield session
    session.close()


def _upload(db, filename: str) -> Document:
    content = (FIXTURES_SAMPLES / filename).read_bytes()
    return process_upload(db, content, "image/jpeg")


def test_admission_form_becomes_student_within_gate_budget(db):
    start = time.perf_counter()
    document = _upload(db, "admission_form.jpg")
    result = commit_document(db, document.id)
    elapsed = time.perf_counter() - start

    assert elapsed < 15.0, f"took {elapsed}s, gate requires < 15s"
    assert result["result"]["entity"] == "student"
    student = db.get(Student, result["result"]["id"])
    assert student is not None
    assert student.admission_no == "ADM09051"


def test_low_confidence_field_triggers_needs_review(db):
    document = _upload(db, "admission_form.jpg")
    assert document.status == DocumentStatus.needs_review  # guardian_phone is 0.6


def test_attendance_sheet_commit_creates_records(db):
    document = _upload(db, "attendance_sheet.jpg")
    result = commit_document(db, document.id)
    assert result["result"] == {"entity": "attendance_records", "created": 3, "skipped": 0}

    stmt = select(AttendanceRecord).where(AttendanceRecord.source_ref == f"document:{document.id}")
    assert len(list(db.scalars(stmt))) == 3


def test_leave_application_commit_creates_teacher_absence(db):
    document = _upload(db, "leave_application.jpg")
    result = commit_document(db, document.id)
    assert result["result"]["entity"] == "teacher_absence"
    absence = db.get(TeacherAbsence, result["result"]["id"])
    assert absence is not None and absence.reason


def test_marks_sheet_commit_has_no_target_entity(db):
    document = _upload(db, "marks_sheet.jpg")
    result = commit_document(db, document.id)
    assert result["result"]["entity"] is None
    assert document.status == DocumentStatus.committed


def test_corrections_applied_before_commit(db):
    # A second admission_form upload -- correct admission_no too, so it doesn't
    # collide with the student the gate-budget test above already committed
    # from the same fixture image.
    document = _upload(db, "admission_form.jpg")
    fields = {
        f.field_name: f
        for f in db.scalars(
            select(ExtractedField).where(ExtractedField.document_id == document.id)
        )
    }

    result = commit_document(
        db,
        document.id,
        [
            {"field_id": fields["admission_no"].id, "corrected_value": "ADM09052"},
            {"field_id": fields["guardian_phone"].id, "corrected_value": "9999999999"},
        ],
    )
    student = db.get(Student, result["result"]["id"])
    assert student is not None
    assert student.admission_no == "ADM09052"
    assert student.guardian_phone == "9999999999"


def test_committing_twice_raises(db):
    document = _upload(db, "leave_application.jpg")
    commit_document(db, document.id)
    with pytest.raises(CommitError):
        commit_document(db, document.id)


def test_unrecognized_image_gets_graceful_fallback_not_a_crash(db):
    content = b"not a real image -- no matching fixture hash"
    document = process_upload(db, content, "image/jpeg")
    assert document.type == "unknown"
    assert document.raw_ai_response is not None
    assert document.raw_ai_response["warnings"]
