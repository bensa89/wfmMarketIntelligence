from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.company import CompanyType


class CompanyCreate(BaseModel):
    name: str
    slug: str
    type: CompanyType
    description: Optional[str] = None
    website: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class CompanyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    slug: str
    type: CompanyType
    description: Optional[str]
    website: Optional[str]
    created_at: datetime
