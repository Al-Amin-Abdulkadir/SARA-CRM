from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.notification import NotificationType


class NotificationCreate(BaseModel):
    customer_id: int | None = None
    type: NotificationType
    title: str
    message: str


class NotificationUpdate(BaseModel):
    is_read: bool | None = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int | None
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime
