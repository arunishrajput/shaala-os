
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, ExtractedField
from app.db.session import get_db
from app.services.documents import (
    CommitError,
    commit_document,
    process_upload,
    read_fields,
    reject_document,
)
from app.services.signals.registry import run_signals
from app.services.vision.fixture import FIXTURES_DIR
from app.ws.manager import manager

router = APIRouter(prefix="/documents", tags=["documents"])

SAMPLE_FILES = {
    "admission_form": "admission_form.jpg",
    "attendance_sheet": "attendance_sheet.jpg",
    "marks_sheet": "marks_sheet.jpg",
    "leave_application": "leave_application.jpg",
}


class FieldCorrection(BaseModel):
    field_id: int
    corrected_value: str


class CommitRequest(BaseModel):
    corrections: list[FieldCorrection] = []


def _summary(doc: Document) -> dict:
    return {
        "id": doc.id,
        "type": doc.type,
        "status": doc.status.value,
        "uploaded_at": doc.uploaded_at,
        "committed_at": doc.committed_at,
    }


def _detail(db: Session, doc: Document) -> dict:
    stmt = select(ExtractedField).where(ExtractedField.document_id == doc.id)
    fields_data = read_fields(list(db.scalars(stmt)))
    return {
        **_summary(doc),
        "original_url": doc.original_url,
        "warnings": (doc.raw_ai_response or {}).get("warnings", []),
        "doc_type_confidence": (doc.raw_ai_response or {}).get("doc_type_confidence"),
        **fields_data,
    }


@router.get("/samples")
def list_samples() -> list[dict]:
    return [
        {"doc_type": doc_type, "label": doc_type.replace("_", " ").title()}
        for doc_type in SAMPLE_FILES
    ]


@router.post("/samples/{doc_type}")
async def try_sample(doc_type: str, db: Session = Depends(get_db)) -> dict:
    filename = SAMPLE_FILES.get(doc_type)
    if filename is None:
        raise HTTPException(status_code=404, detail=f"No sample for doc_type='{doc_type}'.")
    content = (FIXTURES_DIR / "samples" / filename).read_bytes()
    document = process_upload(db, content, "image/jpeg")
    await manager.broadcast("document.uploaded", _summary(document))
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return _detail(db, document)


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> dict:
    documents = []
    for file in files:
        content = await file.read()
        document = process_upload(db, content, file.content_type or "application/octet-stream")
        documents.append(_summary(document))
        await manager.broadcast("document.uploaded", _summary(document))
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return {"documents": documents}


@router.get("")
def list_documents(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(Document).order_by(Document.uploaded_at.desc())
    if status is not None:
        stmt = stmt.where(Document.status == status)
    return [_summary(d) for d in db.scalars(stmt)]


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="No such document.")
    return _detail(db, document)


@router.post("/{document_id}/commit")
async def commit(document_id: int, payload: CommitRequest, db: Session = Depends(get_db)) -> dict:
    try:
        result = commit_document(
            db, document_id, [c.model_dump() for c in payload.corrections]
        )
    except CommitError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    await manager.broadcast("document.committed", result)
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return result


@router.post("/{document_id}/reject")
async def reject(document_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        document = reject_document(db, document_id)
    except CommitError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return _summary(document)
