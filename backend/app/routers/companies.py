import pathlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter()

LOGO_DIR = pathlib.Path("/uploads/logos")
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB

MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/svg+xml": "svg",
}


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


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


@router.post("/{slug}/logo", response_model=CompanyRead)
async def upload_logo(
    slug: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Dateityp: {file.content_type}. Erlaubt: PNG, JPG, SVG.",
        )

    contents = await file.read()
    if len(contents) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Datei zu groß. Maximum: 2 MB.")

    ext = MIME_TO_EXT[file.content_type]

    # Delete old logo file if extension changed
    if company.logo_path:
        old_filename = pathlib.Path(company.logo_path).name
        old_file = LOGO_DIR / old_filename
        if old_file.exists():
            old_file.unlink()

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    dest = LOGO_DIR / f"{slug}.{ext}"
    dest.write_bytes(contents)

    company.logo_path = f"logos/{slug}.{ext}"
    db.commit()
    db.refresh(company)
    return company
