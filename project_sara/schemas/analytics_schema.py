from pydantic import BaseModel


class LeadScoreResponse(BaseModel):
    customer_id: int
    customer_name: str
    score: float
    interaction_count: int
    deal_value: float
    days_since_last_activity: int


class SegmentResponse(BaseModel):
    segment: str
    customer_count: int
    avg_deal_value: float
    avg_lead_score: float


class MetricsResponse(BaseModel):
    total_customers: int
    active_customers: int
    leads: int
    churned: int
    total_deals: int
    open_deals: int
    closed_won: int
    closed_lost: int
    total_revenue: float
    avg_deal_value: float
    avg_lead_score: float
    avg_churn_risk: float
