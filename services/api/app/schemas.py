from pydantic import BaseModel, ConfigDict

from app.db.models import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    linked_id: int | None = None


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    subjects: list[str]
    dept: str
    phone: str
    max_periods_per_week: int
    max_periods_per_day: int


class ClassSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade: str
    section: str
    strength: int


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_no: str
    name: str
    class_id: int
    roll_no: int
    guardian_name: str
    guardian_phone: str
    qr_token: str
    photo_url: str | None = None
