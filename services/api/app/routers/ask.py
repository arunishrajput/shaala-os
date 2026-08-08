from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai.ask import AskError, answer_query

router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    query: str


@router.post("")
def post_ask(body: AskRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return answer_query(db, body.query)
    except AskError as e:
        return {"query": body.query, "intent": None, "answer": str(e), "data": None, "source": None}
