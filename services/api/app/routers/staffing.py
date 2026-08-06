from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.staffing.forecast import backtest, forecast

router = APIRouter(prefix="/staffing", tags=["staffing"])


@router.get("/forecast")
def get_forecast(days: int = 7, db: Session = Depends(get_db)) -> dict:
    return forecast(db, days=days)


@router.get("/backtest")
def get_backtest(days: int = 30, db: Session = Depends(get_db)) -> dict:
    return backtest(db, days=days)
