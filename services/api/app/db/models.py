import enum
from datetime import date as date_
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(enum.StrEnum):
    admin = "admin"
    teacher = "teacher"
    parent = "parent"


class RoomType(enum.StrEnum):
    classroom = "classroom"
    lab = "lab"
    hall = "hall"


class AttendanceStatus(enum.StrEnum):
    present = "present"
    absent = "absent"
    late = "late"


class AttendanceMethod(enum.StrEnum):
    qr = "qr"
    vision = "vision"
    manual = "manual"


class DocumentStatus(enum.StrEnum):
    pending = "pending"
    needs_review = "needs_review"
    committed = "committed"
    rejected = "rejected"


class ActionSeverity(enum.StrEnum):
    critical = "critical"
    warning = "warning"
    info = "info"


class ActionStatus(enum.StrEnum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    academic_year: Mapped[str] = mapped_column(String(20))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    linked_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    subjects: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    max_periods_per_week: Mapped[int] = mapped_column(Integer)
    max_periods_per_day: Mapped[int] = mapped_column(Integer)
    unavailable_slots: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    preferred_slots: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    phone: Mapped[str] = mapped_column(String(20))
    dept: Mapped[str] = mapped_column(String(100))


class ClassSection(Base):
    __tablename__ = "class_sections"
    __table_args__ = (UniqueConstraint("grade", "section", name="uq_grade_section"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[str] = mapped_column(String(10))
    section: Mapped[str] = mapped_column(String(5))
    strength: Mapped[int] = mapped_column(Integer)
    home_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    admission_no: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    class_id: Mapped[int] = mapped_column(ForeignKey("class_sections.id"))
    roll_no: Mapped[int] = mapped_column(Integer)
    guardian_name: Mapped[str] = mapped_column(String(200))
    guardian_phone: Mapped[str] = mapped_column(String(20))
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    weekly_periods: Mapped[int] = mapped_column(Integer)
    needs_lab: Mapped[bool] = mapped_column(Boolean, default=False)
    is_double_period: Mapped[bool] = mapped_column(Boolean, default=False)


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer)
    type: Mapped[RoomType] = mapped_column(Enum(RoomType, name="room_type"))


class TimeSlot(Base):
    __tablename__ = "time_slots"
    __table_args__ = (UniqueConstraint("day", "period", name="uq_day_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[int] = mapped_column(Integer)  # 0-5 (Mon-Sat)
    period: Mapped[int] = mapped_column(Integer)  # 1-8
    start: Mapped[time] = mapped_column(Time)
    end: Mapped[time] = mapped_column(Time)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class_sections.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))


class TimetableVersion(Base):
    __tablename__ = "timetable_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    label: Mapped[str] = mapped_column(String(200))
    solver_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("timetable_versions.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("class_sections.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    is_substitution: Mapped[bool] = mapped_column(Boolean, default=False)
    original_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id"), nullable=True
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    date: Mapped[date_] = mapped_column(Date)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status")
    )
    method: Mapped[AttendanceMethod] = mapped_column(
        Enum(AttendanceMethod, name="attendance_method")
    )
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class TeacherAbsence(Base):
    __tablename__ = "teacher_absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    date: Mapped[date_] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(500))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    original_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )
    raw_ai_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    field_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    was_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(100))
    severity: Mapped[ActionSeverity] = mapped_column(Enum(ActionSeverity, name="action_severity"))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status"), default=ActionStatus.open
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    primary_action: Mapped[str] = mapped_column(String(200))


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    to_name: Mapped[str] = mapped_column(String(200))
    to_phone: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
