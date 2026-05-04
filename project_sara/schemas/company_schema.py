from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from models.company import CompanySize, CompanyStatus


class CompanyCreate(BaseModel):
    name: str
    industry: str | None = None
    website: str | None = None
    size: CompanySize | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: CompanyStatus = CompanyStatus.lead
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    website: str | None = None
    size: CompanySize | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: CompanyStatus | None = None
    notes: str | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str | None
    website: str | None
    size: CompanySize | None
    email: str | None
    phone: str | None
    status: CompanyStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
