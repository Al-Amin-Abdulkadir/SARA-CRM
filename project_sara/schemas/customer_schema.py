from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from models.customer import CustomerStatus


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company_id: int | None = None
    industry: str | None = None
    status: CustomerStatus = CustomerStatus.lead
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company_id: int | None = None
    industry: str | None = None
    status: CustomerStatus | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None
    company_id: int | None
    industry: str | None
    status: CustomerStatus
    notes: str | None
    lead_score: float
    churn_risk: float
    created_at: datetime
    updated_at: datetime
