"""The notification Outbox (PROMPT.md §6.2 point 3, §6.3): drafted, never
auto-sent -- there's no SMS/WhatsApp provider wired up (correctly out of
scope, PROMPT.md §2), so every row here is `status="draft"` and visible for
what it is, not a fake "sent" confirmation.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notification, Student


def draft_parent_messages(db: Session, student_ids: list[int]) -> list[Notification]:
    students = list(db.scalars(select(Student).where(Student.id.in_(student_ids))))
    drafted = []
    for student in students:
        n = Notification(
            to_name=student.guardian_name,
            to_phone=student.guardian_phone,
            channel="sms",
            body=(
                f"Shaala Public School: {student.name}'s attendance fell below 75% "
                "this week. Please contact the class teacher if there's something "
                "we should know."
            ),
            status="draft",
        )
        db.add(n)
        drafted.append(n)
    db.flush()
    return drafted


def draft_substitute_notice(
    db: Session,
    *,
    teacher_name: str,
    teacher_phone: str,
    class_label: str,
    subject_name: str,
    slot_label: str,
    absent_teacher_name: str,
) -> Notification:
    n = Notification(
        to_name=teacher_name,
        to_phone=teacher_phone,
        channel="sms",
        body=(
            f"Shaala Public School: you're covering {subject_name} for {class_label} "
            f"at {slot_label} today, in place of {absent_teacher_name}."
        ),
        status="draft",
    )
    db.add(n)
    db.flush()
    return n
