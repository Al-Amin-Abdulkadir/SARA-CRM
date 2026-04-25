import enum
from datetime import datetime
from sqlalchemy import  String, Enum as SAEnum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.base import Base

class NotificationType(str, enum.Enum):
    churn_alert = "churn_alert"
    deal_update = "deal_update"
    follow_up = "follow_up"
    report = "report"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id : Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True)
    type : Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    title : Mapped[str] = mapped_column(String(200))
    message : Mapped[str] = mapped_column(String(1000))
    is_read : Mapped[bool] = mapped_column(Boolean, default=False)
    created_at : Mapped[datetime] = mapped_column(default=datetime.utcnow)

    customer : Mapped["Customer | None"] = relationship()
