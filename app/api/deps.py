from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.repositories.trainer_repository import TrainerRepository
from app.services.campaign_service import CampaignService
from app.services.pokemon_service import PokemonService
from app.services.ranger_service import RangerService
from app.services.sighting_service import SightingService
from app.services.trainer_service import TrainerService


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pokemon_service(db: Session = Depends(get_db)) -> PokemonService:
    pokemon_repo = PokemonRepository(db)
    return PokemonService(pokemon_repo)


def get_trainer_service(db: Session = Depends(get_db)) -> TrainerService:
    trainer_repo = TrainerRepository(db)
    return TrainerService(trainer_repo)


def get_ranger_service(db: Session = Depends(get_db)) -> RangerService:
    ranger_repo = RangerRepository(db)
    return RangerService(ranger_repo)


def get_campaign_service(db: Session = Depends(get_db)) -> CampaignService:
    campaign_repo = CampaignRepository(db)
    ranger_repo = RangerRepository(db)
    sighting_repo = SightingRepository(db)
    return CampaignService(campaign_repo, ranger_repo, sighting_repo)


def get_sighting_service(db: Session = Depends(get_db)) -> SightingService:
    sighting_repo = SightingRepository(db)
    pokemon_repo = PokemonRepository(db)
    ranger_repo = RangerRepository(db)
    campaign_service = get_campaign_service(db)
    return SightingService(sighting_repo, pokemon_repo, ranger_repo, campaign_service)
