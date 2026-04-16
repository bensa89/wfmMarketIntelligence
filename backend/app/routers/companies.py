from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter()


@router.get("", response_model=List[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    existing = db.query(Company).filter(Company.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{slug}", response_model=CompanyRead)
def get_company(slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{slug}", response_model=CompanyRead)
def update_company(slug: str, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company
