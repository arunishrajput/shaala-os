"""POST /demo/reset (PROMPT.md §11): judges mutate shared demo data at odd
hours; this restores the fixed seed baseline in under 15 seconds.
"""

import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Student, Teacher
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def test_reset_restores_seed_data_within_budget():
    db = SessionLocal()
    try:
        db.execute(
            select(Student).limit(1)
        )  # touch a session so the pool isn't cold for the timing below
    finally:
        db.close()

    start = time.perf_counter()
    resp = client.post("/demo/reset", headers={"X-Reset-Key": "pytest-demo-reset-key"})
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert elapsed < 15, f"reset took {elapsed:.1f}s, over the §11 budget"

    db = SessionLocal()
    try:
        assert db.scalar(select(Student)) is not None
        rao = db.scalar(select(Teacher).where(Teacher.name == "Kavita Rao"))
        assert rao is not None
    finally:
        db.close()
