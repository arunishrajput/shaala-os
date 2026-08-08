"""Principal's Weekly Briefing (PROMPT.md §6.6). No GEMINI_API_KEY is
configured in this environment (see .env.example), so `generate_briefing`
always exercises the deterministic template fallback here -- exactly the
demo-safety path a judge hits on the live URL without a key added.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.main import app
from app.services.ai.briefing import compute_stats, generate_briefing
from app.services.signals import rules  # noqa: F401 -- registers the @signal rules
from app.services.signals.registry import run_signals
from app.services.timetable.solver import generate_timetable

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    generate_timetable(session, label="briefing test")
    run_signals(session, today=DEMO_ANCHOR_DATE)
    yield session
    session.close()


def test_compute_stats_is_aggregates_only(db):
    stats = compute_stats(db, DEMO_ANCHOR_DATE)
    assert stats["as_of"] == DEMO_ANCHOR_DATE.isoformat()
    assert isinstance(stats["open_actions_total"], int)
    assert isinstance(stats["open_actions_by_severity"], dict)
    assert stats["attendance_rate_pct_7d"] is None or isinstance(
        stats["attendance_rate_pct_7d"], (int, float)
    )
    assert isinstance(stats["at_risk_students"], int)
    assert isinstance(stats["documents_pending_review"], int)
    # Never raw rows: no key holds a list of per-student/per-document records.
    for value in stats.values():
        assert not isinstance(value, list)


def test_compute_stats_deterministic_for_the_same_seeded_data(db):
    a = compute_stats(db, DEMO_ANCHOR_DATE)
    b = compute_stats(db, DEMO_ANCHOR_DATE)
    assert a == b


def test_generate_briefing_falls_back_to_template_without_a_gemini_key(db):
    result = generate_briefing(db, DEMO_ANCHOR_DATE)
    assert result["source"] == "template"
    assert isinstance(result["narrative"], str)
    assert len(result["narrative"]) > 0


def test_template_narrative_cites_the_real_attendance_number(db):
    stats = compute_stats(db, DEMO_ANCHOR_DATE)
    result = generate_briefing(db, DEMO_ANCHOR_DATE)
    if stats["attendance_rate_pct_7d"] is not None:
        assert str(stats["attendance_rate_pct_7d"]) in result["narrative"]


def test_template_narrative_mentions_action_center_when_items_are_open(db):
    stats = compute_stats(db, DEMO_ANCHOR_DATE)
    result = generate_briefing(db, DEMO_ANCHOR_DATE)
    if stats["open_actions_total"] > 0:
        assert "Action Center" in result["narrative"]
    else:
        assert "clear" in result["narrative"]


def test_briefing_endpoint_returns_narrative_and_stats():
    resp = client.post("/briefing/generate")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["narrative"], str) and body["narrative"]
    assert "as_of" in body["stats"]
