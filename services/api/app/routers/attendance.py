from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEMO_ANCHOR_DATE
from app.db.models import (
    AttendanceMethod,
    AttendanceRecord,
    AttendanceStatus,
    ClassSection,
    Student,
)
from app.db.session import get_db
from app.services.id_cards import generate_id_cards_pdf
from app.ws.manager import manager

router = APIRouter(tags=["attendance"])


class ScanRequest(BaseModel):
    qr_token: str


class ManualRequest(BaseModel):
    student_id: int
    status: str = "present"


def _record_out(record: AttendanceRecord, student: Student) -> dict:
    return {
        "id": record.id,
        "student_id": student.id,
        "student_name": student.name,
        "class_id": student.class_id,
        "status": record.status.value,
        "method": record.method.value,
        "marked_at": record.marked_at,
        "confidence": record.confidence,
    }


def _today_record(db: Session, student_id: int) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.date == DEMO_ANCHOR_DATE,
        )
    )


@router.post("/attendance/scan")
async def scan(payload: ScanRequest, db: Session = Depends(get_db)) -> dict:
    """Kiosk QR scan (PROMPT.md §6.4A). Attendance is a once-a-day fact, so a
    re-scan of an already-marked card — whether an accidental double-tap
    seconds later or someone scanning again at lunch — is reported as
    "already marked", never a second row or an error.
    """
    student = db.scalar(select(Student).where(Student.qr_token == payload.qr_token))
    if student is None:
        return {"status": "unknown", "message": "Unregistered card."}

    existing = _today_record(db, student.id)
    if existing is not None:
        return {
            "status": "duplicate",
            "message": f"{student.name} already marked.",
            "record": _record_out(existing, student),
        }

    record = AttendanceRecord(
        student_id=student.id,
        date=DEMO_ANCHOR_DATE,
        status=AttendanceStatus.present,
        method=AttendanceMethod.qr,
        source_ref=payload.qr_token,
    )
    db.add(record)
    db.commit()

    out = _record_out(record, student)
    await manager.broadcast("attendance.marked", out)
    return {"status": "marked", "record": out}


@router.post("/attendance/manual")
async def manual(payload: ManualRequest, db: Session = Depends(get_db)) -> dict:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="No such student.")
    try:
        status = AttendanceStatus(payload.status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid status '{payload.status}'.") from e

    record = _today_record(db, student.id)
    if record is not None:
        record.status = status
        record.method = AttendanceMethod.manual
        record.marked_at = datetime.now(UTC)
    else:
        record = AttendanceRecord(
            student_id=student.id,
            date=DEMO_ANCHOR_DATE,
            status=status,
            method=AttendanceMethod.manual,
        )
        db.add(record)
    db.commit()

    out = _record_out(record, student)
    await manager.broadcast("attendance.marked", out)
    return out


@router.post("/attendance/group-photo")
async def group_photo() -> dict:
    raise HTTPException(
        status_code=501,
        detail=(
            "Group-photo attendance is an optional Phase 4 stretch (PROMPT.md §6.4B), "
            "not built this session -- QR scan and manual roll call are the supported paths."
        ),
    )


@router.get("/attendance/today")
def today(db: Session = Depends(get_db)) -> dict:
    stmt = (
        select(AttendanceRecord, Student)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .where(AttendanceRecord.date == DEMO_ANCHOR_DATE)
        .order_by(AttendanceRecord.marked_at.desc())
    )
    rows = db.execute(stmt).all()
    records = [_record_out(r, s) for r, s in rows]
    present = sum(1 for r in records if r["status"] != "absent")
    return {
        "date": DEMO_ANCHOR_DATE.isoformat(),
        "count": len(records),
        "present": present,
        "records": records,
    }


@router.get("/attendance/student/{student_id}/summary")
def student_summary(student_id: int, days: int = 30, db: Session = Depends(get_db)) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="No such student.")
    window_start = DEMO_ANCHOR_DATE - timedelta(days=days)
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.date >= window_start,
        AttendanceRecord.date <= DEMO_ANCHOR_DATE,
    )
    records = list(db.scalars(stmt))
    total = len(records)
    present = sum(1 for r in records if r.status != AttendanceStatus.absent)
    pct = round(100 * present / total, 1) if total else None
    return {
        "student_id": student_id,
        "student_name": student.name,
        "days": days,
        "total_records": total,
        "present_days": present,
        "attendance_pct": pct,
    }


@router.get("/students/id-cards.pdf")
def id_cards(class_id: int | None = None, db: Session = Depends(get_db)) -> Response:
    stmt = select(Student).order_by(Student.class_id, Student.roll_no)
    if class_id is not None:
        stmt = stmt.where(Student.class_id == class_id)
    students = list(db.scalars(stmt))
    if not students:
        raise HTTPException(status_code=404, detail="No students match that filter.")
    sections = {s.id: s for s in db.scalars(select(ClassSection))}
    pdf_bytes = generate_id_cards_pdf(students, sections)
    return Response(content=pdf_bytes, media_type="application/pdf")
