from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security import get_current_user
from app.services.ai.briefing import generate_briefing

router = APIRouter(prefix="/briefing", tags=["briefing"], dependencies=[Depends(get_current_user)])


@router.post("/generate")
def post_generate(db: Session = Depends(get_db)) -> dict:
    return generate_briefing(db)
