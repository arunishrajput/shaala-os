"""Staffing forecast (PROMPT.md §6.5): EWMA + seasonal baseline over real
TeacherAbsence history, plus a runtime-computed backtest accuracy number.
"""

import pytest

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.services.staffing.forecast import backtest, forecast


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    yield session
    session.close()


def test_forecast_covers_every_department_for_the_requested_days(db):
    result = forecast(db, days=7, as_of=DEMO_ANCHOR_DATE)
    assert result["as_of"] == DEMO_ANCHOR_DATE.isoformat()
    assert len(result["departments"]) == 8  # DEPARTMENTS in seed.py
    for dept in result["departments"]:
        assert len(dept["days"]) == 7
        for day in dept["days"]:
            assert day["expected_absences"] >= 0
            assert day["expected_uncovered_periods"] >= 0


def test_backtest_produces_a_runtime_computed_accuracy_number(db):
    result = backtest(db, days=30, as_of=DEMO_ANCHOR_DATE)
    assert result["mae"] is not None
    assert result["mae"] >= 0
    assert result["accuracy_pct"] is not None
    assert 0 <= result["accuracy_pct"] <= 100
    assert len(result["points"]) > 0
    # Not hardcoded: a different as_of produces different numbers.
    other = backtest(db, days=30, as_of=DEMO_ANCHOR_DATE.replace(day=1))
    assert other["points"] != result["points"]


def test_forecast_is_deterministic_for_the_same_seeded_data(db):
    a = forecast(db, days=7, as_of=DEMO_ANCHOR_DATE)
    b = forecast(db, days=7, as_of=DEMO_ANCHOR_DATE)
    assert a == b
