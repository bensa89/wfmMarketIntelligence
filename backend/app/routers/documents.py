from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentRead

router = APIRouter()


@router.get("", response_model=List[DocumentRead])
def list_documents(source_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if source_id:
        query = query.filter(Document.source_id == source_id)
    return query.order_by(Document.crawled_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
