from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.base import Base
import enum

class InteractionType(str, enum.Enum):
    call = "call"
    email = "email"
    meeting = "meeting"
    note = "note"


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    type: Mapped[InteractionType] = mapped_column(SAEnum(InteractionType))
    summary: Mapped[str] = mapped_column(String(500))
    outcome: Mapped[str | None] = mapped_column(String(300))
    occurred_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="interactions")