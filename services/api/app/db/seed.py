"""Fixed-seed demo data (PROMPT.md §5). Deterministic: same output every run and
every redeploy, so the deployed app always matches the recorded demo video.

Note on class sections: PROMPT.md §5 says "12 sections (6-A -> 10-B, plus 11/12
Science & Commerce)" but the product pitch (§1) names "9-A, 10-B and 11-C" as Mrs.
Rao's classes -- "11-C" isn't producible under a strict Science/Commerce reading,
and a literal 6-A..10-B (5 grades x 2) + 11/12 Science & Commerce (2 grades x 2)
is 14 sections, not 12. Since the pitch narrative is explicitly "the story every
feature serves" (memorized, demo-critical) while the section-naming aside is a
secondary parenthetical, this seed resolves the conflict in the narrative's favor:
grade 6 gets one section, grades 7-10 get two (A/B), grade 11 gets three (A/B/C) --
exactly 12 sections, and 9-A / 10-B / 11-C all exist for the Mrs. Rao story.
"""

import hashlib
import hmac
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import insert, text

from app.config import settings
from app.db.models import (
    ActionItem,
    ActionSeverity,
    ActionStatus,
    AttendanceMethod,
    AttendanceRecord,
    AttendanceStatus,
    ClassSection,
    Document,
    DocumentStatus,
    Room,
    RoomType,
    School,
    Student,
    Subject,
    Teacher,
    TeacherAbsence,
    TimeSlot,
    User,
    UserRole,
)
from app.db.session import SessionLocal
from app.security import hash_password

SEED = 42

# Fixed so re-seeding on a different calendar day still reproduces byte-identical
# data (PROMPT.md §11: "the deployed app looks identical to your video").
ANCHOR_DATE = date(2026, 8, 5)

DEPARTMENTS = [
    "English",
    "Hindi",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Social Studies",
    "Computer Science",
]

# name, code, weekly_periods, needs_lab, is_double_period
_SUBJECT_ROWS = [
    ("English", "ENG", 5, False, False),
    ("Hindi", "HIN", 4, False, False),
    ("Mathematics", "MATH", 6, False, False),
    ("Physics", "PHY", 5, True, False),
    ("Chemistry", "CHEM", 5, True, False),
    ("Biology", "BIO", 4, False, False),
    ("Social Studies", "SST", 4, False, False),
    ("Computer Science", "CS", 3, True, True),
]
SUBJECT_DEFS = [
    {
        "name": name,
        "code": code,
        "weekly_periods": weekly_periods,
        "needs_lab": needs_lab,
        "is_double_period": is_double_period,
    }
    for name, code, weekly_periods, needs_lab, is_double_period in _SUBJECT_ROWS
]

SECTION_DEFS = [
    ("6", "A"),
    ("7", "A"), ("7", "B"),
    ("8", "A"), ("8", "B"),
    ("9", "A"), ("9", "B"),
    ("10", "A"), ("10", "B"),
    ("11", "A"), ("11", "B"), ("11", "C"),
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Krishna", "Ishaan",
    "Rohan", "Kabir", "Ananya", "Diya", "Saanvi", "Aadhya", "Kavya", "Myra",
    "Anika", "Ira", "Riya", "Sara", "Meera", "Kavita", "Priya", "Neha",
    "Sanjay", "Rajesh", "Suresh", "Vikram", "Anil", "Sunita", "Pooja", "Deepa",
]
LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Rao", "Gupta", "Nair", "Reddy", "Kumar",
    "Singh", "Patel", "Menon", "Joshi", "Desai", "Kapoor", "Chatterjee", "D'Souza",
    "Bhatt", "Mehta", "Pillai", "Bose", "Rana", "Choudhary", "Agarwal", "Bhandari",
]

# Physics dept teachers named to match the "explain any cell" example in
# PROMPT.md §6.2 verbatim ("Mr. Khan is the only free Physics teacher — Ms. Iyer
# has 11-C now") and the Mrs. Rao pitch story (§1).
PHYSICS_NAMES = ["Kavita Rao", "Meera Iyer", "Aslam Khan", "Vikram Nair", "Sunita Desai"]

DEMO_USERS: list[tuple[str, UserRole]] = [
    ("admin@shaala.demo", UserRole.admin),
    ("teacher@shaala.demo", UserRole.teacher),
    ("parent@shaala.demo", UserRole.parent),
]

TABLES_IN_DELETE_ORDER = [
    "event_logs",
    "notifications",
    "action_items",
    "extracted_fields",
    "documents",
    "teacher_absences",
    "attendance_records",
    "timetable_entries",
    "timetable_versions",
    "assignments",
    "students",
    "class_sections",
    "time_slots",
    "subjects",
    "rooms",
    "teachers",
    "users",
    "schools",
]


def qr_token_for(admission_no: str) -> str:
    key = settings.jwt_secret.encode() or b"dev-only-fixed-key"
    return hmac.new(key, admission_no.encode(), hashlib.sha256).hexdigest()[:20]


def wipe(db) -> None:
    for table in TABLES_IN_DELETE_ORDER:
        db.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
    db.commit()


def seed_school(db) -> School:
    school = School(name="Shaala Public School", academic_year="2026-27")
    db.add(school)
    db.flush()
    return school


def seed_rooms(db) -> dict[str, Room]:
    rooms = {}
    for i in range(1, 9):
        r = Room(name=f"Room {100 + i}", capacity=60, type=RoomType.classroom)
        db.add(r)
        rooms[r.name] = r
    for name in ["Physics Lab", "Chemistry Lab", "Computer Lab"]:
        r = Room(name=name, capacity=40, type=RoomType.lab)
        db.add(r)
        rooms[name] = r
    hall = Room(name="Assembly Hall", capacity=500, type=RoomType.hall)
    db.add(hall)
    rooms[hall.name] = hall
    db.flush()
    return rooms


def seed_subjects(db) -> dict[str, Subject]:
    subjects: dict[str, Subject] = {}
    for s in SUBJECT_DEFS:
        subj = Subject(
            name=s["name"],
            code=s["code"],
            weekly_periods=s["weekly_periods"],
            needs_lab=s["needs_lab"],
            is_double_period=s["is_double_period"],
        )
        db.add(subj)
        subjects[str(s["name"])] = subj
    db.flush()
    return subjects


def seed_sections(db) -> list[ClassSection]:
    sections = []
    for grade, section in SECTION_DEFS:
        cs = ClassSection(grade=grade, section=section, strength=50)
        db.add(cs)
        sections.append(cs)
    db.flush()
    return sections


def seed_time_slots(db) -> list[TimeSlot]:
    slots = []
    period_starts = [
        time(8, 0), time(8, 45), time(9, 30), time(10, 15),
        time(11, 0), time(11, 45), time(12, 30), time(13, 15),
    ]
    for day in range(6):  # Mon-Sat
        for period, start in enumerate(period_starts, start=1):
            end_minutes = start.hour * 60 + start.minute + 45
            end = time(end_minutes // 60, end_minutes % 60)
            slot = TimeSlot(
                day=day,
                period=period,
                start=start,
                end=end,
                is_break=(period == 5),  # lunch
            )
            db.add(slot)
            slots.append(slot)
    db.flush()
    return slots


def seed_teachers(db, rng: random.Random) -> dict[str, list[Teacher]]:
    by_dept: dict[str, list[Teacher]] = {}
    code_n = 1
    for dept in DEPARTMENTS:
        teachers = []
        if dept == "Physics":
            names = PHYSICS_NAMES
        else:
            names = [f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" for _ in range(5)]
        for name in names:
            t = Teacher(
                name=name,
                code=f"T{code_n:03d}",
                subjects=[dept],
                max_periods_per_week=28,
                max_periods_per_day=6,
                unavailable_slots=[],
                preferred_slots=[],
                phone=f"9{rng.randint(100000000, 999999999)}",
                dept=dept,
            )
            db.add(t)
            teachers.append(t)
            code_n += 1
        by_dept[dept] = teachers
    db.flush()

    # 3 tightly constrained teachers, deliberately not Mrs. Rao (PROMPT.md §5: "make
    # 2-3 tightly constrained so the solver has genuine pressure to relieve").
    tight = [by_dept["Physics"][2], by_dept["Mathematics"][0], by_dept["Chemistry"][1]]
    for t in tight:
        t.max_periods_per_week = 10
        # Unavailable every Wednesday (day=2).
        t.unavailable_slots = []  # filled in after time slots exist; see seed_main

    return by_dept


def seed_assignments(
    db,
    sections: list[ClassSection],
    subjects: dict[str, Subject],
    teachers_by_dept: dict[str, list[Teacher]],
) -> None:
    from app.db.models import Assignment

    sections_by_name = {f"{s.grade}-{s.section}": s for s in sections}
    rao = teachers_by_dept["Physics"][0]
    preassigned_physics = {
        sections_by_name["9-A"].id: rao,
        sections_by_name["10-B"].id: rao,
        sections_by_name["11-C"].id: rao,
    }

    for subj_name, subject in subjects.items():
        dept_teachers = teachers_by_dept[subj_name]
        running_load = {t.id: 0 for t in dept_teachers}
        preassigned = preassigned_physics if subj_name == "Physics" else {}

        ordered_sections = []
        for sec in sections:
            if sec.id in preassigned:
                t = preassigned[sec.id]
                running_load[t.id] += subject.weekly_periods
                db.add(Assignment(class_id=sec.id, subject_id=subject.id, teacher_id=t.id))
            else:
                ordered_sections.append(sec)

        idx = 0
        for sec in ordered_sections:
            chosen = None
            for _ in range(len(dept_teachers)):
                t = dept_teachers[idx % len(dept_teachers)]
                idx += 1
                if running_load[t.id] + subject.weekly_periods <= t.max_periods_per_week:
                    chosen = t
                    break
            if chosen is None:
                chosen = min(dept_teachers, key=lambda t: running_load[t.id])
            running_load[chosen.id] += subject.weekly_periods
            db.add(Assignment(class_id=sec.id, subject_id=subject.id, teacher_id=chosen.id))
    db.flush()


def seed_students(db, sections: list[ClassSection], rng: random.Random) -> list[Student]:
    students = []
    admission_seq = 1
    for sec in sections:
        for roll in range(1, sec.strength + 1):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            name = f"{first} {last}"
            g_first = rng.choice(FIRST_NAMES)
            admission_no = f"ADM{admission_seq:05d}"
            student = Student(
                admission_no=admission_no,
                name=name,
                class_id=sec.id,
                roll_no=roll,
                guardian_name=f"{g_first} {last}",
                guardian_phone=f"9{rng.randint(100000000, 999999999)}",
                qr_token=qr_token_for(admission_no),
                photo_url=None,
            )
            db.add(student)
            students.append(student)
            admission_seq += 1
    db.flush()
    return students


def pick_cliff_students(students: list[Student], rng: random.Random) -> list[int]:
    """The 6 students deliberately trending toward the 75% attendance cliff.
    Pure — no DB access — so callers can commit core people data (and create the
    demo users that reference these ids) before the slow attendance bulk load runs.
    """
    return [s.id for s in rng.sample(students, 6)]


def seed_attendance(
    db,
    students: list[Student],
    sections: list[ClassSection],
    cliff_ids: set[int],
    rng: random.Random,
) -> None:
    """90 days of textured history ending the day before ANCHOR_DATE."""
    flu_section = sections[3]  # "8-A"
    flu_week_start = ANCHOR_DATE - timedelta(days=23)
    festival_dip_start = ANCHOR_DATE - timedelta(days=52)
    last_week_start = ANCHOR_DATE - timedelta(days=7)

    records = []
    for offset in range(1, 91):
        day = ANCHOR_DATE - timedelta(days=offset)
        if day.weekday() == 6:  # Sunday — no school
            continue

        is_monday = day.weekday() == 0
        is_festival_week = festival_dip_start <= day < festival_dip_start + timedelta(days=6)
        is_flu_week = flu_week_start <= day < flu_week_start + timedelta(days=6)
        is_last_week = day >= last_week_start

        for student in students:
            if student.id in cliff_ids and is_last_week:
                present_prob = 0.15  # forces "6 students drop below 75% this week"
            else:
                present_prob = 0.94
                if is_monday:
                    present_prob -= 0.06
                if is_festival_week:
                    present_prob -= 0.15
                if is_flu_week and student.class_id == flu_section.id:
                    present_prob -= 0.35

            draw = rng.random()
            if draw < present_prob:
                status = AttendanceStatus.late if rng.random() < 0.04 else AttendanceStatus.present
            else:
                status = AttendanceStatus.absent

            method_roll = rng.random()
            if method_roll < 0.80:
                method = AttendanceMethod.qr
            elif method_roll < 0.95:
                method = AttendanceMethod.manual
            else:
                method = AttendanceMethod.vision

            confidence = (
                round(rng.uniform(0.7, 0.99), 2) if method == AttendanceMethod.vision else None
            )
            marked_at = datetime.combine(day, time(8, rng.randint(0, 30)))

            records.append(
                {
                    "student_id": student.id,
                    "date": day,
                    "status": status,
                    "method": method,
                    "marked_at": marked_at,
                    "confidence": confidence,
                    "source_ref": None,
                }
            )

    # Explicit multi-row VALUES batches, not one execute() per row — over a
    # high-latency connection (e.g. a remote managed Postgres), relying on the
    # driver's default executemany behavior for ~46k rows made this pathologically
    # slow (one network round trip per row).
    chunk_size = 2000
    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        db.execute(insert(AttendanceRecord).values(chunk))
        db.commit()
    db.flush()


def seed_flavor_data(
    db,
    teachers_by_dept: dict[str, list[Teacher]],
    students: list[Student],
    cliff_student_ids: list[int],
) -> None:
    db.add(
        ActionItem(
            kind="low_attendance_trend",
            severity=ActionSeverity.critical,
            title="6 students drop below 75% this week",
            body="6 students across multiple sections fell under 75% attendance this week.",
            payload={"student_ids": cliff_student_ids},
            status=ActionStatus.open,
            primary_action="Draft parent messages",
        )
    )
    db.add(
        ActionItem(
            kind="documents_need_review",
            severity=ActionSeverity.warning,
            title="2 scanned forms need review",
            body="2 uploaded documents have low-confidence fields awaiting review.",
            payload={},
            status=ActionStatus.open,
            primary_action="Review now",
        )
    )
    db.add(
        ActionItem(
            kind="room_conflict",
            severity=ActionSeverity.info,
            title="Chem Lab double-booked Thu P5",
            body="Two sections are scheduled in the Chemistry Lab at the same time.",
            payload={},
            status=ActionStatus.open,
            primary_action="Resolve",
        )
    )

    # 2 pending documents. original_url points at fixtures that Phase 3 will add —
    # the vision pipeline itself doesn't exist yet (stubbed loudly, not silently).
    db.add(
        Document(
            type="leave_application",
            original_url="fixtures/sample_leave_application.jpg",
            status=DocumentStatus.pending,
            raw_ai_response=None,
        )
    )
    db.add(
        Document(
            type="admission_form",
            original_url="fixtures/sample_admission_form.jpg",
            status=DocumentStatus.pending,
            raw_ai_response=None,
        )
    )

    # 1 unresolved absence — a different teacher from Mrs. Rao, whose absence is
    # meant to be triggered live during the demo (Phase 4), not pre-seeded.
    other_teacher = teachers_by_dept["Hindi"][0]
    db.add(
        TeacherAbsence(
            teacher_id=other_teacher.id,
            date=ANCHOR_DATE - timedelta(days=1),
            reason="Personal leave",
            resolved=False,
        )
    )


def seed_users(
    db, teachers_by_dept: dict[str, list[Teacher]], cliff_student_ids: list[int]
) -> None:
    rao = teachers_by_dept["Physics"][0]
    parent_student_id = cliff_student_ids[0]
    demo_password_hash = hash_password("demo1234")
    links: dict[UserRole, int | None] = {
        UserRole.admin: None,
        UserRole.teacher: rao.id,
        UserRole.parent: parent_student_id,
    }
    for email, role in DEMO_USERS:
        db.add(
            User(
                email=email,
                password_hash=demo_password_hash,
                role=role,
                linked_id=links[role],
            )
        )


def main() -> None:
    db = SessionLocal()
    rng = random.Random(SEED)
    try:
        wipe(db)
        seed_school(db)
        rooms = seed_rooms(db)
        subjects = seed_subjects(db)
        sections = seed_sections(db)
        time_slots = seed_time_slots(db)
        teachers_by_dept = seed_teachers(db, rng)

        wednesday_slot_ids = [s.id for s in time_slots if s.day == 2 and not s.is_break]
        tight = [
            teachers_by_dept["Physics"][2],
            teachers_by_dept["Mathematics"][0],
            teachers_by_dept["Chemistry"][1],
        ]
        for t in tight:
            t.unavailable_slots = wednesday_slot_ids

        seed_assignments(db, sections, subjects, teachers_by_dept)
        students = seed_students(db, sections, rng)
        cliff_student_ids = pick_cliff_students(students, rng)
        seed_flavor_data(db, teachers_by_dept, students, cliff_student_ids)
        seed_users(db, teachers_by_dept, cliff_student_ids)
        db.commit()
        print(
            f"Core data committed: {len(sections)} sections, "
            f"{sum(len(v) for v in teachers_by_dept.values())} teachers, "
            f"{len(students)} students, {len(rooms)} rooms, {len(time_slots)} time slots."
        )

        # Slowest part (~46k rows) — committed in its own chunks (see
        # seed_attendance) so a partial run still leaves the core data intact.
        seed_attendance(db, students, sections, set(cliff_student_ids), rng)
        print("Attendance history committed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
