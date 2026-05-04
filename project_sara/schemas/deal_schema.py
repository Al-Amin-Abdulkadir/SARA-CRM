from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from models.deal import DealStage


class DealCreate(BaseModel):
    customer_id: int
    title: str
    value: float = 0.0
    stage: DealStage = DealStage.lead
    expected_close_date: date | None = None
    actual_close_date: date | None = None
    notes: str | None = None


class DealUpdate(BaseModel):
    title: str | None = None
    value: float | None = None
    stage: DealStage | None = None
    expected_close_date: date | None = None
    actual_close_date: date | None = None
    notes: str | None = None


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    title: str
    value: float
    stage: DealStage
    expected_close_date: date | None
    actual_close_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
