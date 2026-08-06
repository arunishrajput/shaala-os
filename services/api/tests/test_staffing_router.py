"""GET /staffing/forecast and /staffing/backtest -- the router wiring on top
of services/staffing/forecast.py, which has its own math-focused tests in
test_staffing.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import seed as seed_module
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def db():
    seed_module.main()


def test_forecast_endpoint():
    resp = client.get("/staffing/forecast", params={"days": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 7
    assert len(body["departments"]) == 8


def test_backtest_endpoint():
    resp = client.get("/staffing/backtest", params={"days": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mae"] is not None
    assert body["accuracy_pct"] is not None
