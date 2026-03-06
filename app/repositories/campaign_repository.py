from sqlalchemy.orm import Session

from app.models import Campaign
from app.repositories.base_repository import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self, db: Session):
        super().__init__(db, Campaign)
