from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClassSection, Student, Teacher
from app.db.session import get_db
from app.schemas import ClassSectionOut, StudentOut, TeacherOut
from app.security import get_current_user

router = APIRouter(tags=["people"], dependencies=[Depends(get_current_user)])


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db)) -> list[Teacher]:
    return list(db.scalars(select(Teacher).order_by(Teacher.name)))


@router.get("/teachers/{teacher_id}", response_model=TeacherOut)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)) -> Teacher:
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.get("/students", response_model=list[StudentOut])
def list_students(class_id: int | None = None, db: Session = Depends(get_db)) -> list[Student]:
    stmt = select(Student).order_by(Student.name)
    if class_id is not None:
        stmt = stmt.where(Student.class_id == class_id)
    return list(db.scalars(stmt))


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/classes", response_model=list[ClassSectionOut])
def list_classes(db: Session = Depends(get_db)) -> list[ClassSection]:
    return list(db.scalars(select(ClassSection).order_by(ClassSection.grade, ClassSection.section)))
