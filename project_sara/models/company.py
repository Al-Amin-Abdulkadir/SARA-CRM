from datetime import datetime
from sqlalchemy import Enum  as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.base import Base
import enum

class CompanySize(str, enum.Enum):
    startup = "startup"
    small = "small"
    medium = "medium"
    enterprise = "enterprise"

class CompanyStatus(str, enum.Enum):
    lead = "lead"
    active = "active"
    inactive = "inactive"
    churned = "churned"




class Company(Base):
    __tablename__ = "companies"


    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    name : Mapped[str] = mapped_column(String(150), unique=True, index=True)
    industry : Mapped[str | None] = mapped_column(String(100))
    website : Mapped[str | None] = mapped_column(String(200))
    size : Mapped[CompanySize | None] = mapped_column(SAEnum(CompanySize))
    notes : Mapped[str | None] = mapped_column(String(500))
    email : Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone : Mapped[str | None] = mapped_column(String(20))
    status : Mapped[CompanyStatus] = mapped_column(
        SAEnum(CompanyStatus), default=CompanyStatus.lead
    )
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at : Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    customers : Mapped[list["Customer"]] = relationship(back_populates="company_rel")



    