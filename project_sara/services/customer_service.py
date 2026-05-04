from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session
from models.customer import Customer as CustomerModel, CustomerStatus, JourneyStage
from models.deal import Deal, DealStage
from models.interaction import Interaction
from schemas.customer_schema import CustomerCreate, CustomerUpdate



def _paginate(query, page: int, page_size: int):
    return query.offset((page - 1) * page_size).limit(page_size)


def _apply_date_filter(query, date_from: datetime | None, date_to: datetime | None):
    if date_from:
        query = query.filter(CustomerModel.created_at >= date_from)
    if date_to:
        query = query.filter(CustomerModel.created_at <= date_to)
    return query


def _days_since(dt: datetime | None) -> int:
    if not dt:
        return 9999
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days



class ClientCRUDService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, page: int = 1, page_size: int = 20, sort_by: str = "created_at"):
        query = self.db.query(CustomerModel)
        query = query.order_by(getattr(CustomerModel, sort_by))
        return _paginate(query, page, page_size).all()

    def get_by_id(self, client_id: int) -> CustomerModel | None:
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == client_id)
            .first()
        )

    def get_by_email(self, email: str) -> CustomerModel | None:
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.email == email)
            .first()
        )

    def create(self, data: CustomerCreate) -> CustomerModel:
        client = CustomerModel(**data.model_dump())
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def update(self, client_id: int, data: CustomerUpdate):
        client = self.get_by_id(client_id)
        if not client:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(client, field, value)
        
        self.db.commit()
        self.db.refresh(client)
        return client

    def soft_delete(self, client_id: int):
        client = self.get_by_id(client_id)
        if not client:
            return None
        client.status = CustomerStatus.inactive
        self.db.commit()
        return True

    def update_preferences(self, client_id: int, preferences: dict):
        client = self.get_by_id(client_id)
        if not client:
            return None
        
        client.preferences = {**(client.preferences or {}), **preferences}
        self.db.commit()
        self.db.refresh(client)
        return client
    
class ClientSearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str):
        term = f"%{query}%"
        return (
            self.db.query(CustomerModel)
            .filter(
                or_(
                    CustomerModel.name.ilike(term),
                    CustomerModel.email.ilike(term),
                    CustomerModel.phone.ilike(term)
                )
            )
            .all()
        )

    def filter_by(
        self,
        status: CustomerStatus | None = None,
        industry: str | None = None,
        company_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[CustomerModel]:
        
        query = self.db.query(CustomerModel)
        if status:
            query = query.filter(CustomerModel.status == status)
        
        if industry:
            query = query.filter(CustomerModel.industry == industry)
        
        if company_id:
            query = query.filter(CustomerModel.company_id == company_id)
        
        query = _apply_date_filter(query, date_from, date_to)
        return query.all()
        

    def get_by_status(self, status: CustomerStatus):
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.status == status)
        ).all()

    def get_by_company(self, company_id: int):
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.company_id == company_id)
        ).all()
    
    def get_by_industry(self, industry: str):
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.industry == industry)
        ).all()
    def get_recently_added(self, days: int = 30):
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.created_at >= cutoff)
            .order_by(CustomerModel.created_at.desc())
        ).all()
        
class ClientLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.client_service = ClientCRUDService(db)

    def convert_lead_to_active(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        client.status = CustomerStatus.active
        client.journey_stage = JourneyStage.onboarding
        self.db.commit()
        self.db.refresh(client)
        return client

    def mark_as_churned(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        client.status = CustomerStatus.churned
        client.journey_stage = JourneyStage.at_risk
        self.db.commit()
        self.db.refresh(client)
        return client
        

    def get_full_profile(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        return {
            "client" : client,
            "company" : client.company_rel,
            "interactions" : client.interactions,
            "deals" : client.deals,
            "interaction_count" : len(client.interactions),
            "deals_count" : len(client.deals),
            "total_deal_value" : sum(d.value for d in client.deals),
        }
        

    def get_last_interaction(self, client_id: int):
        return (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id).order_by(
                Interaction.occurred_at.desc()
            ).first()
        )

    def get_inactive_clients(self, days_threshold: int = 30):
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_threshold)
        active_client_ids = (
            self.db.query(Interaction.customer_id)
            .filter(Interaction.occurred_at >= cutoff)
            .distinct()
            .subquery()
        )
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id.not_in(active_client_ids))
            .filter(CustomerModel.status == CustomerStatus.active)
            .all()
        )

    def update_lead_score(self, client_id: int, score: float):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        client.lead_score = score
        self.db.commit()
        self.db.refresh(client)
        return client

    def update_churn_risk(self, client_id: int, risk: float):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        client.churn_risk = risk
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_high_risk_clients(self, threshold: float = 0.7 ) -> list[CustomerModel]:
        clients = self.db.query(CustomerModel).filter(
            CustomerModel.churn_risk >= threshold
        ).order_by(
            CustomerModel.churn_risk.desc()
        ).all()

        return clients

    def get_top_scored_leads(self, limit: int = 10):
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.status == CustomerStatus.lead)
            .order_by(CustomerModel.lead_score.desc())
            .limit(limit)
            .all()
        )
        
    def get_client_timeline(self, client_id: int):
       interactions = (
           self.db.query(Interaction).filter(
               Interaction.customer_id == client_id
           ).all()
       )

       deals = (
           self.db.query(Deal).filter(
               Deal.customer_id == client_id
           ).all()
       )

       timeline = []

       for i in interactions:
           timeline.append({
               "type" : "interaction",
               "subtype" : i.type.value,
               "summary" : i.summary,
               "date" : i.occurred_at,
           })

       for d in deals:
           timeline.append({
               "type" : "deal",
               "title" : d.title,
               "stage" : d.stage.value,
               "value" : d.value,
               "date" : d.created_at
           })

       return sorted(timeline, key=lambda x : x["date"], reverse=True)

    def get_client_summary_stats(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        deals = client.deals
        interactions = client.interactions
        won = [d for d in deals if d.stage == DealStage.closed_won]
        lost = [d for d in deals if d.stage == DealStage.closed_lost]
        last = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .first()
        )

        return {
            "client_id" : client_id,
            "name" : client.name,
            "total_deals" : len(deals),
            "won_deals" : len(won),
            "lost_deals" : len(lost),
            "win_rate" : round(len(won) / len(deals) * 100, 1) if deals else 0.0,
            "total_revenue" : sum(d.value for d in won),
            "interaction_count" : len(interactions),
            "days_since_last_contact" : _days_since(last.occurred_at) if last else 9999,
            "lead_score" : client.lead_score,
            "churn_risk" : client.churn_risk,
            "health_score" : client.health_score,
        }
    

    def get_clients_needing_followup(self, days: int = 7):
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        recent_contact_ids = (
            self.db.query(Interaction.customer_id)
            .filter(Interaction.occurred_at >= cutoff)
            .distinct()
            .subquery()
        )

        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id.not_in(recent_contact_ids))
            .filter(CustomerModel.status == CustomerStatus.active)
            .all()
        )
       

    def get_at_risk_with_open_deals(self, threshold : float = 0.6):
        open_stages = [DealStage.lead, DealStage.contacted, DealStage.negotiation]
        return (
            self.db.query(CustomerModel)
            .join(Deal, Deal.customer_id == CustomerModel.id)
            .filter(CustomerModel.churn_risk >= threshold)
            .filter(Deal.stage.in_(open_stages))
            .distinct()
            .all()
        )

    def calculate_health_score(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None 
        
        interaction = client.interactions
        deals = client.deals

        last = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .first()
        )

        days = _days_since(last.occurred_at if last else None)

        if days <= 7:
            recency_score = 30
        elif days <= 30:
            recency_score = 20
        elif days <= 60:
            recency_score = 10
        else:
            recency_score = 0

        interaction_score = min(30, len(interaction) * 3)
        open_stages = [DealStage.lead, DealStage.contacted, DealStage.negotiation]
        has_open = any(d.stage in open_stages for d in deals)
        has_won = any(d.stage == DealStage.closed_won for d in deals)
        deal_score = (10 if has_open else 0) + (10 if has_won else 0)

        churn_penalty = client.churn_risk * 20

        score = recency_score + interaction_score + deal_score - churn_penalty
        score = round(max(0.0, min (100.0, score)), 2)

        client.health_score = score
        self.db.commit()
        self.db.refresh(client)
        return client

    def update_journey_stage(self, client_id: int, stage: JourneyStage):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        client.journey_stage = stage
        self.db.commit()
        self.db.refresh(client)
        return client

    def generate_client_summary(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        deals = client.deals
        interactions = client.interactions

        won = [d for d in deals if d.stage == DealStage.closed_won]
        lost = [d for d in deals if d.stage == DealStage.closed_lost]
        last = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .first()
        )

        days_since_last_contact = _days_since(last.occurred_at if last else None)


        return {
            "client_id" : client_id,
            "name" : client.name,
            "email" : client.email,
            "status" : client.status,
            "journey_stage" : client.journey_stage,
            "interctions" : len(interactions),
            "total_deals" : len(deals),
            "won_deals" : len(won),
            "lost_deals" : len(lost),
            "total_revenue" : sum(d.value for d in won),
            "days_since_last_contact" : days_since_last_contact
        }



    def track_interaction_frequency(self, client_id: int):
        pass

    def track_engagement_status(self, client_id: int):
        pass

    def generate_insights(self, client_id: int):
        pass

    def get_re_engagement_candidates(self, days_inactive: int = 30):
        pass

    def get_communication_summary(self, client_id: int):
        pass

    def predict_next_best_action(self, client_id: int):
        pass


class ClientAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def count_by_status(self):
        pass

    def count_by_industry(self):
        pass

    def get_new_clients_this_period(self, date_from: datetime, date_to: datetime):
        pass

    def get_interaction_count(self, client_id: int):
        pass

    def bulk_update_status(self, client_ids: list[int], new_status: CustomerStatus):
        pass

    def bulk_assign_to_company(self, client_ids: list[int], company_id: int):
        pass

    def detect_duplicates(self, client_id: int):
        pass

    def merge_clients(self, primary_id: int, duplicate_id: int):
        pass

    def export_clients(self, filters: dict | None = None):
        pass

    def calculate_clv(self, client_id: int):
        pass

    def find_similar_clients(self, client_id: int):
        pass

    def rank_by_clv(self, limit: int = 10):
        pass

    def rank_by_engagement(self, limit: int = 10):
        pass

    def get_conversion_rate(self, client_id: int):
        pass

    def get_rfm_score(self, client_id: int):
        pass
