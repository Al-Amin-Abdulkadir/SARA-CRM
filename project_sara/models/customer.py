import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Enum as SAENUM, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base


class CustomerStatus(str, enum.Enum):
    lead = "lead"
    active = "active"
    inactive = "inactive"
    churned = "churned"


class JourneyStage(str, enum.Enum):
    prospect = "prospect"
    onboarding = "onboarding"
    active = "active"
    at_risk = "at_risk"
    champion = "champion"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    industry: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[CustomerStatus] = mapped_column(
        SAENUM(CustomerStatus), default=CustomerStatus.lead
    )
    journey_stage: Mapped[JourneyStage] = mapped_column(
        SAENUM(JourneyStage), default=JourneyStage.prospect
    )
    preferences: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None]
    lead_score: Mapped[float] = mapped_column(Float, default=0.0)
    churn_risk: Mapped[float] = mapped_column(Float, default=0.0)
    health_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="customer")
    deals: Mapped[list["Deal"]] = relationship(back_populates="customer")
    company_rel: Mapped["Company | None"] = relationship(back_populates="customers")
    