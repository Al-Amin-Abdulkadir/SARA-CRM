from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.interaction import InteractionType


class InteractionCreate(BaseModel):
    customer_id: int
    type: InteractionType
    summary: str
    outcome: str | None = None
    occurred_at: datetime | None = None


class InteractionUpdate(BaseModel):
    type: InteractionType | None = None
    summary: str | None = None
    outcome: str | None = None
    occurred_at: datetime | None = None


class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    type: InteractionType
    summary: str
    outcome: str | None
    occurred_at: datetime
    created_at: datetime
