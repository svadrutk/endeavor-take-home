from sqlalchemy import func

from app.models import Campaign, CampaignStatus, Ranger, Sighting
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.schemas import CampaignCreate, CampaignUpdate


class CampaignService:
    def __init__(
        self,
        campaign_repo: CampaignRepository,
        ranger_repo: RangerRepository,
        sighting_repo: SightingRepository,
    ):
        self.campaign_repo = campaign_repo
        self.ranger_repo = ranger_repo
        self.sighting_repo = sighting_repo

    def create_campaign(
        self, campaign_data: CampaignCreate, ranger_id: str
    ) -> tuple[Campaign, Ranger]:
        ranger = self.ranger_repo.get(ranger_id)
        if not ranger:
            raise ValueError(
                f"Ranger with ID '{ranger_id}' not found. Only rangers can create campaigns."
            )

        if campaign_data.end_date <= campaign_data.start_date:
            raise ValueError("end_date must be after start_date")

        campaign = self.campaign_repo.create(
            {
                "name": campaign_data.name,
                "description": campaign_data.description,
                "region": campaign_data.region,
                "start_date": campaign_data.start_date,
                "end_date": campaign_data.end_date,
                "status": CampaignStatus.DRAFT,
            }
        )

        return campaign, ranger

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        return self.campaign_repo.get(campaign_id)

    def update_campaign(self, campaign_id: str, campaign_data: CampaignUpdate) -> Campaign:
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.ACTIVE]:
            raise ValueError(
                f"Cannot update campaign in '{campaign.status}' state. "
                "Only draft and active campaigns can be modified."
            )

        update_data = campaign_data.model_dump(exclude_unset=True)

        if "start_date" in update_data or "end_date" in update_data:
            start_date = update_data.get("start_date", campaign.start_date)
            end_date = update_data.get("end_date", campaign.end_date)
            if end_date <= start_date:
                raise ValueError("end_date must be after start_date")

        return self.campaign_repo.update(campaign, update_data)

    def transition_campaign(self, campaign_id: str, new_status: CampaignStatus) -> Campaign:
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        current_status = CampaignStatus(campaign.status)

        if not current_status.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition campaign from '{current_status}' to '{new_status}'. "
                "Campaigns can only move forward through the lifecycle: "
                "draft → active → completed → archived."
            )

        return self.campaign_repo.update(campaign, {"status": new_status})

    def validate_sighting_campaign(self, campaign_id: str) -> Campaign:
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        if campaign.status != CampaignStatus.ACTIVE:
            raise ValueError(
                f"Cannot add sighting to campaign '{campaign.name}' (status: {campaign.status}). "
                "Only active campaigns can accept new sightings."
            )

        return campaign

    def check_sighting_lock(self, sighting: Sighting) -> None:
        if sighting.campaign_id:
            campaign = self.campaign_repo.get(sighting.campaign_id)
            if campaign and campaign.status == CampaignStatus.COMPLETED:
                raise ValueError(
                    f"Cannot modify sighting: it belongs to completed campaign '{campaign.name}'. "
                    "Completed campaign sightings are locked."
                )

    def get_campaign_summary(self, campaign_id: str) -> dict:
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        db = self.sighting_repo.db

        summary_result = (
            db.query(
                func.count(Sighting.id).label("total_sightings"),
                func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
                func.min(Sighting.date).label("earliest_date"),
                func.max(Sighting.date).label("latest_date"),
            )
            .filter(Sighting.campaign_id == campaign_id)
            .first()
        )

        rangers = (
            db.query(Ranger.name, func.count(Sighting.id).label("sighting_count"))
            .join(Sighting, Ranger.id == Sighting.ranger_id)
            .filter(Sighting.campaign_id == campaign_id)
            .group_by(Ranger.id)
            .order_by(func.count(Sighting.id).desc())
            .all()
        )

        total_sightings = getattr(summary_result, "total_sightings", 0) or 0
        unique_species = getattr(summary_result, "unique_species", 0) or 0
        earliest_date = getattr(summary_result, "earliest_date", None)
        latest_date = getattr(summary_result, "latest_date", None)

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "total_sightings": total_sightings,
            "unique_species": unique_species,
            "contributing_rangers": [
                {"name": r.name, "sightings": r.sighting_count} for r in rangers
            ],
            "observation_date_range": {
                "start": earliest_date,
                "end": latest_date,
            },
        }
