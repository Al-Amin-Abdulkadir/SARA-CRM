import enum
from sqlalchemy import Enum as SAENUM, Float, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.base import Base
from datetime import datetime



class CustomerStatus(str, enum.Enum):
    lead = "lead"
    active = "active"
    inactive = "inactive"
    churned = "churned"



class Customer(Base):
    __tablename__ = "customers"

    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    name : Mapped[str] = mapped_column(String(100))
    email : Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone : Mapped[str | None] = mapped_column(String(20))
    company_id : Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    industry : Mapped[str | None] = mapped_column(String(100))
    status : Mapped[CustomerStatus] = mapped_column(
        SAENUM(CustomerStatus), default=CustomerStatus.lead
    )

    notes : Mapped[str | None]
    lead_score : Mapped[float] = mapped_column(Float, default=0.0)
    churn_risk : Mapped[float] = mapped_column(Float, default=0.0)
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at : Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    interactions : Mapped[list["Interaction"]] = relationship(back_populates="customer")
    deals : Mapped[list["Deal"]] = relationship(back_populates="customer")
    company_rel : Mapped["Company | None"] = relationship(back_populates="customers")
    