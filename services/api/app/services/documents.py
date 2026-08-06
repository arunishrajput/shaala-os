"""The document pipeline (PROMPT.md §6.1): preprocess -> extract -> persist.
Tabular rows are flattened into ExtractedField rows named "row{i}.{key}" so
the same was_corrected/corrected_value correction mechanism works uniformly
for both plain fields and table cells; `read_rows` reconstructs the table.
"""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    AttendanceMethod,
    AttendanceRecord,
    AttendanceStatus,
    ClassSection,
    Document,
    DocumentStatus,
    ExtractedField,
    Student,
    Teacher,
    TeacherAbsence,
)
from app.security import qr_token_for
from app.services.vision.base import DOC_TYPES, ExtractionResult, get_extraction
from app.services.vision.preprocess import PreprocessError, preprocess_image

CONFIDENCE_THRESHOLD = 0.85


class CommitError(Exception):
    """Raised when a document's extracted fields can't be committed as-is —
    the API surfaces this as a 4xx with a plain-English reason, never a crash."""


def _to_data_uri(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode()
    return f"data:{mime_type};base64,{encoded}"


def _is_low_confidence(result: ExtractionResult) -> bool:
    if any(f.confidence < CONFIDENCE_THRESHOLD for f in result.fields):
        return True
    return any(float(r.get("confidence", 1.0)) < CONFIDENCE_THRESHOLD for r in result.rows)


def process_upload(
    db: Session, content: bytes, mime_type: str, uploaded_by: int | None = None
) -> Document:
    try:
        processed = preprocess_image(content)
        stored_mime = "image/jpeg"  # preprocess_image always re-encodes as JPEG
    except PreprocessError:
        # Don't block the upload on a preprocessing failure — store the original.
        processed, stored_mime = content, mime_type

    if settings.vision_provider == "fixture":
        # Fixture replay is keyed by content hash — preprocessing always
        # re-encodes the image (different bytes even if visually identical),
        # which would break hash matching for the "Try a sample" images. Hash
        # the original upload instead; only Gemini benefits from the cleaned-up
        # version.
        result = get_extraction(content, mime_type, "fixture")
    else:
        result = get_extraction(processed, stored_mime, settings.vision_provider)
    doc_type = result.doc_type if result.doc_type in DOC_TYPES else "unknown"
    status = DocumentStatus.needs_review if _is_low_confidence(result) else DocumentStatus.pending

    document = Document(
        type=doc_type,
        original_url=_to_data_uri(processed, stored_mime),
        status=status,
        raw_ai_response={
            "doc_type": result.doc_type,
            "doc_type_confidence": result.doc_type_confidence,
            "warnings": result.warnings,
        },
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.flush()

    for f in result.fields:
        db.add(
            ExtractedField(
                document_id=document.id,
                field_name=f.name,
                value=f.value,
                confidence=f.confidence,
                bbox=f.bbox,
            )
        )

    for i, row in enumerate(result.rows):
        row_confidence = float(row.get("confidence", 1.0))
        row_bbox = row.get("bbox")
        for key, value in row.items():
            if key in ("confidence", "bbox"):
                continue
            db.add(
                ExtractedField(
                    document_id=document.id,
                    field_name=f"row{i}.{key}",
                    value=str(value),
                    confidence=row_confidence,
                    bbox=row_bbox,
                )
            )

    db.commit()
    db.refresh(document)
    return document


def read_fields(fields: list[ExtractedField]) -> dict:
    """Splits a document's flat ExtractedField list back into top-level fields
    and reconstructed table rows, using each field's current (possibly
    corrected) value."""
    plain: list[ExtractedField] = []
    rows: dict[int, dict] = {}

    for f in fields:
        if f.field_name.startswith("row") and "." in f.field_name:
            prefix, key = f.field_name.split(".", 1)
            try:
                idx = int(prefix.removeprefix("row"))
            except ValueError:
                plain.append(f)
                continue
            rows.setdefault(idx, {})[key] = f.corrected_value if f.was_corrected else f.value
        else:
            plain.append(f)

    return {
        "fields": [
            {
                "id": f.id,
                "name": f.field_name,
                "value": f.corrected_value if f.was_corrected else f.value,
                "original_value": f.value,
                "confidence": f.confidence,
                "bbox": f.bbox,
                "was_corrected": f.was_corrected,
            }
            for f in plain
        ],
        "rows": [rows[i] for i in sorted(rows)],
    }


def apply_corrections(db: Session, document_id: int, corrections: list[dict]) -> None:
    for c in corrections:
        f = db.get(ExtractedField, c["field_id"])
        if f is not None and f.document_id == document_id:
            f.corrected_value = c["corrected_value"]
            f.was_corrected = True
    db.flush()


def _values(fields_data: dict) -> dict[str, str]:
    return {f["name"]: f["value"] for f in fields_data["fields"]}


def _find_section(db: Session, class_label: str) -> ClassSection:
    grade, _, section = class_label.partition("-")
    row = db.scalar(
        select(ClassSection).where(
            ClassSection.grade == grade.strip(), ClassSection.section == section.strip()
        )
    )
    if row is None:
        raise CommitError(f"No class section matches '{class_label}'.")
    return row


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as e:
        raise CommitError(f"Could not parse date '{value}' (expected ISO 8601).") from e


def commit_admission_form(db: Session, document: Document, fields_data: dict) -> dict:
    v = _values(fields_data)
    name = v.get("student_name", "").strip()
    admission_no = v.get("admission_no", "").strip()
    class_label = v.get("class_label", "").strip()
    if not name or not admission_no or not class_label:
        raise CommitError("student_name, admission_no, and class_label are required.")

    section = _find_section(db, class_label)

    if db.scalar(select(Student).where(Student.admission_no == admission_no)) is not None:
        raise CommitError(f"A student with admission_no '{admission_no}' already exists.")

    try:
        roll_no = int(v.get("roll_no", "0").strip())
    except ValueError:
        roll_no = 0

    student = Student(
        admission_no=admission_no,
        name=name,
        class_id=section.id,
        roll_no=roll_no,
        guardian_name=v.get("guardian_name", "").strip(),
        guardian_phone=v.get("guardian_phone", "").strip(),
        qr_token=qr_token_for(admission_no),
        photo_url=None,
    )
    db.add(student)
    db.flush()
    return {"entity": "student", "id": student.id, "name": student.name, "class": class_label}


def commit_attendance_sheet(db: Session, document: Document, fields_data: dict) -> dict:
    v = _values(fields_data)
    class_label = v.get("class_label", "").strip()
    if not class_label:
        raise CommitError("class_label is required.")
    section = _find_section(db, class_label)
    record_date = _parse_date(v.get("date", ""))

    created, skipped = 0, 0
    for row in fields_data["rows"]:
        try:
            roll_no = int(str(row.get("roll_no", "")).strip())
        except ValueError:
            skipped += 1
            continue
        student = db.scalar(
            select(Student).where(Student.class_id == section.id, Student.roll_no == roll_no)
        )
        status_raw = str(row.get("status", "")).strip().lower()
        if student is None or status_raw not in ("present", "absent", "late"):
            skipped += 1
            continue
        db.add(
            AttendanceRecord(
                student_id=student.id,
                date=record_date,
                status=AttendanceStatus(status_raw),
                method=AttendanceMethod.manual,
                confidence=None,
                source_ref=f"document:{document.id}",
            )
        )
        created += 1
    db.flush()
    return {"entity": "attendance_records", "created": created, "skipped": skipped}


def commit_leave_application(db: Session, document: Document, fields_data: dict) -> dict:
    v = _values(fields_data)
    teacher_code = v.get("teacher_code", "").strip()
    if not teacher_code:
        raise CommitError("teacher_code is required.")
    teacher = db.scalar(select(Teacher).where(Teacher.code == teacher_code))
    if teacher is None:
        raise CommitError(f"No teacher with code '{teacher_code}'.")
    leave_date = _parse_date(v.get("leave_date", ""))

    absence = TeacherAbsence(
        teacher_id=teacher.id,
        date=leave_date,
        reason=v.get("reason", "").strip() or "Leave application",
        resolved=False,
    )
    db.add(absence)
    db.flush()
    return {"entity": "teacher_absence", "id": absence.id, "teacher": teacher.name}


def commit_marks_sheet(db: Session, document: Document, fields_data: dict) -> dict:
    # No target table -- Shaala OS deliberately doesn't store grades or generate
    # report cards (PROMPT.md §2). The extraction itself (reviewable, correctable)
    # is still real; committing just archives it as reviewed.
    return {
        "entity": None,
        "note": "Marks are archived only; Shaala OS does not store grades (out of scope).",
    }


COMMIT_HANDLERS = {
    "admission_form": commit_admission_form,
    "attendance_sheet": commit_attendance_sheet,
    "leave_application": commit_leave_application,
    "marks_sheet": commit_marks_sheet,
}


def commit_document(db: Session, document_id: int, corrections: list[dict] | None = None) -> dict:
    document = db.get(Document, document_id)
    if document is None:
        raise CommitError(f"No document with id={document_id}")
    if document.status == DocumentStatus.committed:
        raise CommitError("Document is already committed.")

    if corrections:
        apply_corrections(db, document_id, corrections)

    stmt = select(ExtractedField).where(ExtractedField.document_id == document_id)
    fields_data = read_fields(list(db.scalars(stmt)))

    handler = COMMIT_HANDLERS.get(document.type)
    if handler is None:
        raise CommitError(f"Don't know how to commit doc_type='{document.type}'.")

    result = handler(db, document, fields_data)

    document.status = DocumentStatus.committed
    document.committed_at = datetime.now(UTC)
    db.commit()
    db.refresh(document)
    return {
        "document_id": document.id,
        "doc_type": document.type,
        "status": document.status.value,
        "result": result,
    }


def reject_document(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise CommitError(f"No document with id={document_id}")
    document.status = DocumentStatus.rejected
    db.commit()
    db.refresh(document)
    return document
