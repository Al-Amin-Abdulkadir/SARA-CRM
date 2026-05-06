from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy import func
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
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        interactions = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .all()
        )

        if not interactions:
            return {
                "client_id" : client_id,
                "total" : 0,
                "first_contact" : None,
                "last_contact" : None,
                "days_active" : 0,
                "avg_per_week" : 0.0
            }
        
        first = interactions[0].occurred_at
        last = interactions[-1].occurred_at
        days_active = (last - first).days or 1
        weeks_active = days_active / 7

        return {
            "client_id" : client_id,
            "total" : len(interactions),
            "first_contact" : first,
            "last_contact" : last,
            "days_active" : days_active,
            "avg_per_week" : round(len(interactions) / weeks_active, 2)
        }
    
    def track_engagement_status(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        interactions = client.interactions
        last = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .first()
        )

        days_since_last_contact = _days_since(last.occurred_at if last else None)
        total = len(interactions)

        if days_since_last_contact == 9999:
            status = "never contacted"
        elif days_since_last_contact  <= 7 and total  >= 5:
            status = "highly_engaged"
        elif days_since_last_contact <= 30:
            status = "engaged"
        elif days_since_last_contact <= 60:
            status = "cooling_off"
        
        else:
            status = "dormant"

        return {
            "client_id" : client_id,
            "engagement_status" : status,
            "days_since_last_contact" : days_since_last_contact,
            "interaction_count" : total
        }


    def generate_insights(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        client_engagements = self.track_engagement_status(client_id)
        client_summary_stats = self.get_client_summary_stats(client_id)
        client_interaction_frequency = self.track_interaction_frequency(client_id)

        insights = []

        if client.churn_risk >= 0.7:
            insights.append("High Churn risk - immediate attention required. ")

        if client_engagements["engagement_status"] in ["dormant", "cooling_off"]:
            insights.append(f"client has not been contacted in {client_engagements['days_since_last_contact']} days. Schedula a follow up. ")

        if client_summary_stats["win_rate"] >= 70:
            insights.append(f"Strong win rate of {client_summary_stats['win_rate']}%. Consider upselling opportunities. ")
        
        if client.health_score < 40:
            insights.append("Low hwalth score! Review interaction history and open deals.")
        
        if client_interaction_frequency["avg_per_week"] < 0.5:
            insights.append("Low interaction frequency. Consider increasing touchpoints. ")
        
        if not insights:
            insights.append("Client is in good standing with no immediate concerns")

        return {
            "client_id" : client_id,
            "name" : client.name,
            "insights" : insights
        }

    def get_re_engagement_candidates(self, days_inactive: int = 30):
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_inactive)
        active_clients = (
            self.db.query(Interaction.customer_id)
            .filter(Interaction.occurred_at >= cutoff)
            .distinct()
            .subquery()
        )

        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id.not_in(active_clients))
            .filter(CustomerModel.status == CustomerStatus.active)
            .filter(CustomerModel.churn_risk < 0.9)
            .order_by(CustomerModel.churn_risk.desc())
            .all()
        )
    
    def get_communication_summary(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        interactions = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .all()
        )

        if not interactions:
            return {
                "client_id" : client_id,
                "name" : client.name,
                "total_interactions" : 0,
                "by_type" : {

                },
                "last_contact_date" : None,
                "days_since_last_contact" : 9999
            }
        
        by_type = {}
        for type in interactions:
            key = type.type.value
            by_type[key] = by_type.get(key, 0) + 1

        last = interactions[0] 
     
        return {
            "client_id" : client_id,
            "name" : client.name,
            "total_interactions" : len(interactions),
            "by_type" : by_type,
            "last_contact_date" : last.occurred_at,
            "days_since_last_contact" : _days_since(last.occurred_at)
        }

    def predict_next_best_action(self, client_id: int):
        client = self.client_service.get_by_id(client_id)
        if not client:
            return None
        
        engagement = self.track_engagement_status(client_id)
        stats = self.get_client_summary_stats(client_id)


        status = engagement["engagement_status"]
        days = engagement["days_since_last_contact"]

        if status == "never_contacted":
            action = "send an introduction email"
            reason = "Client has never been contacted"
        
        elif client.churn_risk >= 0.7:
            action = "Arrange an urgent meeting"
            reason = f"High churn risk of {client.churn_risk}"
        elif status in ("dormant", "cooling_off"):
            action = "Schedule a check-in call"
            reason = f"No contact in {days} days"
        elif stats["total_deals"] > 0 and status == "engaged":
            action = "Follow up on open deals"
            reason = "Client is engaged with active deals in pipeline"
        elif stats["win_rate"] >= 70 and client.health_score >= 70:
            action = "Explore upsell opportunities"
            reason = f"Strong win rate of {stats['win_rate']}% and healthy score"
        else:
            action = "Maintain regular contact"
            reason = "Client is in good standing"

        return {
            "client_id" : client_id,
            "name" : client.name,
            "recommended_action" : action,
            "reason" : reason
        }
        

class ClientAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.client_servive = ClientCRUDService(db)

    def count_by_status(self):
        results = (
            self.db.query(CustomerModel.status, func.count(CustomerModel.id))
            .group_by(CustomerModel.status)
            .all()
        )

        return {
            status.value : count for status, count in results
        }

    def count_by_industry(self):
        results = (
            self.db.query(CustomerModel.industry, func.count(CustomerModel.id))
            .filter(CustomerModel.industry.isnot(None))
            .group_by(CustomerModel.industry)
            .all()
        )

        return {
            industry: count for industry, count in results
        }

    def get_new_clients_this_period(self, date_from: datetime, date_to: datetime):
        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.created_at >= date_from)
            .filter(CustomerModel.created_at <= date_to)
            .order_by(CustomerModel.created_at.desc())
            .all()
        )

    def get_interaction_count(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None
        
        interactions = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .count()
        )

        return {
            "client_id" : client_id,
            "Interaction_count" : interactions
        }

    def bulk_update_status(self, client_ids: list[int], new_status: CustomerStatus):
        clients = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id.in_(client_ids))
            .all()
        )

        for client in clients:
            client.status = new_status

        self.db.commit()
        
        return {
            
            "updated" : len(clients)
        }

    def bulk_assign_to_company(self, client_ids: list[int], company_id: int):
        clients = (
            
            self.db.query(CustomerModel)
            .filter(CustomerModel.id.in_(client_ids))
            .all()
        )

        for client in clients:
            client.company_id = company_id

        self.db.commit()
        return {

            "updated" : len(clients)
        }

    def detect_duplicates(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None
        
        matches = (
            
            self.db.query(CustomerModel)
            .filter(CustomerModel.id != client_id)
            .filter(
                or_(
                    CustomerModel.email == client.email,
                    CustomerModel.name == client.name
                )
            )
            .all()
        )

        return {
            "client_id" : client_id,
            "duplicates_found"  : len(matches),
            "duplicates" : [
                {
                    "id" : m.id,
                    "name" : m.name,
                    "email" : m.email
                }
                
                for m in matches
            ]
        }

    def merge_clients(self, primary_id: int, duplicate_id: int):
        primary = self.client_servive.get_by_id(primary_id)
        duplicate = self.client_servive.get_by_id(duplicate_id)
        if not primary or not duplicate:
            return None

        for interaction in duplicate.interactions:
            interaction.customer_id = primary_id

        for deal in duplicate.deals:
            deal.customer_id = primary_id

        if not primary.phone and duplicate.phone:
            primary.phone = duplicate.phone
        if not primary.industry and duplicate.industry:
            primary.industry = duplicate.industry
        if not primary.notes and duplicate.notes:
            primary.notes = duplicate.notes

        duplicate.status = CustomerStatus.inactive

        self.db.commit()
        self.db.refresh(primary)
        return primary

    def export_clients(self, filters: dict | None = None):
        query = self.db.query(CustomerModel)
        if filters:
            if filters.get("status"):
                query = query.filter(CustomerModel.status == filters["status"])
            if filters.get("industry"):
                query = query.filter(CustomerModel.industry == filters["industry"])
            if filters.get("company_id"):
                query = query.filter(CustomerModel.company_id == filters["company_id"])

        clients = query.all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "status": c.status.value,
                "industry": c.industry,
                "journey_stage": c.journey_stage.value,
                "lead_score": c.lead_score,
                "churn_risk": c.churn_risk,
                "health_score": c.health_score,
                "created_at": c.created_at,
            }
            for c in clients
        ]

    def calculate_clv(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None

        won_deals = [d for d in client.deals if d.stage == DealStage.closed_won]
        total_revenue = sum(d.value for d in won_deals)

        days_active = _days_since(client.created_at)
        years_active = max(days_active / 365, 1)
        avg_annual_revenue = total_revenue / years_active
        clv = avg_annual_revenue * 3

        return {
            "client_id": client_id,
            "name": client.name,
            "total_revenue": round(total_revenue, 2),
            "avg_annual_revenue": round(avg_annual_revenue, 2),
            "estimated_clv": round(clv, 2),
        }

    def find_similar_clients(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None

        return (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id != client_id)
            .filter(
                or_(
                    CustomerModel.industry == client.industry,
                    CustomerModel.company_id == client.company_id
                )
            )
            .filter(CustomerModel.status == client.status)
            .all()
        )

    def rank_by_clv(self, limit: int = 10):
        clients = self.db.query(CustomerModel).all()
        ranked = []
        for client in clients:
            won_deals = [d for d in client.deals if d.stage == DealStage.closed_won]
            total_revenue = sum(d.value for d in won_deals)
            ranked.append({"id": client.id, "name": client.name, "total_revenue": total_revenue})

        ranked.sort(key=lambda x: x["total_revenue"], reverse=True)
        return ranked[:limit]

    def rank_by_engagement(self, limit: int = 10):
        results = (
            self.db.query(
                CustomerModel.id,
                CustomerModel.name,
                func.count(Interaction.id).label("interaction_count")
            )
            .join(Interaction, Interaction.customer_id == CustomerModel.id)
            .group_by(CustomerModel.id, CustomerModel.name)
            .order_by(func.count(Interaction.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {"id": r.id, "name": r.name, "interaction_count": r.interaction_count}
            for r in results
        ]

    def get_conversion_rate(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None

        deals = client.deals
        if not deals:
            return {"client_id": client_id, "name": client.name, "conversion_rate": 0.0}

        won = [d for d in deals if d.stage == DealStage.closed_won]
        rate = round(len(won) / len(deals) * 100, 1)

        return {
            "client_id": client_id,
            "name": client.name,
            "total_deals": len(deals),
            "won_deals": len(won),
            "conversion_rate": rate,
        }

    def get_rfm_score(self, client_id: int):
        client = self.client_servive.get_by_id(client_id)
        if not client:
            return None

        last = (
            self.db.query(Interaction)
            .filter(Interaction.customer_id == client_id)
            .order_by(Interaction.occurred_at.desc())
            .first()
        )
        days = _days_since(last.occurred_at if last else None)

        if days <= 7:
            recency = 5
        elif days <= 30:
            recency = 4
        elif days <= 60:
            recency = 3
        elif days <= 90:
            recency = 2
        else:
            recency = 1

        count = len(client.interactions)
        if count >= 20:
            frequency = 5
        elif count >= 10:
            frequency = 4
        elif count >= 5:
            frequency = 3
        elif count >= 2:
            frequency = 2
        else:
            frequency = 1

        won_deals = [d for d in client.deals if d.stage == DealStage.closed_won]
        revenue = sum(d.value for d in won_deals)
        if revenue >= 100000:
            monetary = 5
        elif revenue >= 50000:
            monetary = 4
        elif revenue >= 10000:
            monetary = 3
        elif revenue >= 1000:
            monetary = 2
        else:
            monetary = 1

        return {
            "client_id": client_id,
            "name": client.name,
            "recency": recency,
            "frequency": frequency,
            "monetary": monetary,
            "rfm_score": recency + frequency + monetary,
        }
