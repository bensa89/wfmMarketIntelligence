from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.company import Company
from app.models.search_run import SearchRun
from app.models.search_result import SearchResult
from app.models.source import Source
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.schemas.search import (
    SearchRunRead,
    SearchResultRead,
    SourceCandidateRead,
    SourceCandidateApprove,
)
from app.searcher.pipeline import run_search_all_companies, run_search_for_company

search_router = APIRouter()
candidates_router = APIRouter()


@search_router.post("/run")
def search_run_all(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return run_search_all_companies(db)


@search_router.post("/run/{company_id}")
def search_run_company(
    company_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return run_search_for_company(company, db)


@search_router.get("/runs", response_model=List[SearchRunRead])
def list_search_runs(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchRun).options(selectinload(SearchRun.query))
    if company_id:
        q = q.join(SearchRun.query).filter(SearchRun.query.has(company_id=company_id))
    return q.order_by(SearchRun.executed_at.desc()).limit(100).all()


@search_router.get("/results", response_model=List[SearchResultRead])
def list_search_results(
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SearchResult)
    if run_id:
        q = q.filter(SearchResult.search_run_id == run_id)
    return q.order_by(SearchResult.discovered_at.desc()).limit(200).all()


@candidates_router.get("/", response_model=List[SourceCandidateRead])
def list_source_candidates(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SourceCandidate)
    if status:
        q = q.filter(SourceCandidate.status == status)
    if company_id:
        q = q.filter(SourceCandidate.company_id == company_id)
    return q.order_by(SourceCandidate.created_at.desc()).all()


@candidates_router.post("/{candidate_id}/approve")
def approve_source_candidate(
    candidate_id: str,
    body: SourceCandidateApprove,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = (
        db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    source = Source(
        company_id=candidate.company_id,
        url=candidate.url,
        label=body.label or candidate.title,
        source_type=body.source_type,
        is_active=True,
    )
    db.add(source)

    candidate.status = SourceCandidateStatus.monitored
    db.commit()

    return {"status": "approved", "source_id": source.id}


@candidates_router.post("/{candidate_id}/reject")
def reject_source_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    candidate = (
        db.query(SourceCandidate).filter(SourceCandidate.id == candidate_id).first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.status = SourceCandidateStatus.rejected
    db.commit()
    return {"status": "rejected"}
