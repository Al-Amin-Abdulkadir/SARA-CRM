from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ReportRequest(BaseModel):
    report_type: str
    date_from: date
    date_to: date


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_type: str
    date_from: date
    date_to: date
    generated_at: datetime
    data: dict
