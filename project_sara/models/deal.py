from datetime import date,  datetime
from sqlalchemy import String, Float, ForeignKey, Enum as SAEnum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.base import Base
import enum


class DealStage(str, enum.Enum):
    lead = "lead"
    contacted = "contacted"
    negotiation = "negotiation"
    closed_won = "closed_won"
    closed_lost = "closed_lost"

class Deal(Base):
    __tablename__ = "deals"

    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id : Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    title : Mapped[str] = mapped_column(String(200))
    value : Mapped[float] = mapped_column(Float,  default=0.0)
    stage : Mapped[DealStage] = mapped_column(SAEnum(DealStage), default=DealStage.lead)
    expected_close_date : Mapped[date | None] = mapped_column(Date)
    actual_close_date : Mapped[date | None] = mapped_column(Date)
    notes : Mapped[str | None] = mapped_column(String(500))
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at : Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    customer : Mapped["Customer"] = relationship(back_populates="deals")