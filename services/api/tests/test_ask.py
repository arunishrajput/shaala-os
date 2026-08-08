"""Ask Shaala (PROMPT.md §6.6). No GEMINI_API_KEY is configured in this
environment, so `answer_query` always exercises the deterministic keyword
fallback here -- the same path a judge hits on the live URL without a key
added. Each case below is chosen to land on a different whitelisted intent,
so this doubles as coverage that every function in `_WHITELIST` is reachable
and returns a well-formed answer, never a crash.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.main import app
from app.services.ai.ask import _UNKNOWN_INTENT_ANSWER, answer_query
from app.services.timetable.solver import generate_timetable

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    generate_timetable(session, label="ask test")
    yield session
    session.close()


def test_who_is_free_parses_day_and_period_and_returns_free_teachers(db):
    result = answer_query(db, "Who's free Tuesday period 3?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "who_is_free"
    assert result["source"] == "fallback"
    assert result["data"]["day"] == "Tue"
    assert result["data"]["period"] == 3
    assert "period 3" in result["answer"]


def test_who_is_free_missing_day_gives_a_plain_error_not_a_crash(db):
    # Mentions "period" (so the fallback matcher picks who_is_free) but no
    # day name, so the function itself -- not the matcher -- has to reject it.
    result = answer_query(db, "Who's free period 3?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "who_is_free"
    assert "day" in result["answer"].lower()
    assert result["data"] is None


def test_who_is_free_too_vague_falls_outside_the_whitelist(db):
    # No day, no period -- genuinely not enough to guess an intent from.
    result = answer_query(db, "Who is free?", DEMO_ANCHOR_DATE)
    assert result["intent"] is None
    assert result["data"] is None


def test_attendance_rate_for_a_named_class(db):
    result = answer_query(db, "What's the attendance rate for 10-A this week?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "attendance_rate"
    assert result["data"]["class_label"] == "10-A"
    assert 0 <= result["data"]["rate_pct"] <= 100


def test_attendance_rate_whole_school_when_no_class_named(db):
    result = answer_query(db, "How's attendance doing?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "attendance_rate"
    assert result["data"]["class_label"] is None
    assert "whole school" in result["answer"]


def test_uncovered_classes_today(db):
    result = answer_query(db, "Which classes are uncovered today?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "uncovered_classes_today"
    assert result["data"]["count"] >= 0


def test_students_at_risk(db):
    result = answer_query(db, "Which students are at risk?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "students_at_risk"
    assert result["data"]["count"] >= 0


def test_staffing_shortfall(db):
    result = answer_query(db, "Is any department short-staffed next week?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "staffing_shortfall"
    assert result["data"]["count"] >= 0


def test_documents_pending(db):
    result = answer_query(db, "How many documents need review?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "documents_pending"
    assert result["data"]["count"] >= 0


def test_room_conflicts(db):
    result = answer_query(db, "Are there any room conflicts?", DEMO_ANCHOR_DATE)
    assert result["intent"] == "room_conflicts"
    assert result["data"]["count"] >= 0


def test_unrecognized_question_gets_the_whitelist_boundary_answer(db):
    result = answer_query(db, "What's the capital of France?", DEMO_ANCHOR_DATE)
    assert result["intent"] is None
    assert result["answer"] == _UNKNOWN_INTENT_ANSWER
    assert result["data"] is None


def test_empty_query_raises_ask_error(db):
    from app.services.ai.ask import AskError

    with pytest.raises(AskError):
        answer_query(db, "   ", DEMO_ANCHOR_DATE)


def test_ask_endpoint_returns_a_well_formed_answer():
    resp = client.post("/ask", json={"query": "Who's free Wednesday period 2?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "who_is_free"
    assert isinstance(body["answer"], str) and body["answer"]


def test_ask_endpoint_never_500s_on_a_blank_query():
    resp = client.post("/ask", json={"query": ""})
    assert resp.status_code == 200
    assert resp.json()["intent"] is None
