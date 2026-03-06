import uuid
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException
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


def validate_uuid_format(user_id: str) -> bool:
    try:
        uuid.UUID(user_id)
        return True
    except ValueError:
        return False


def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db),
) -> dict:
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide valid credentials.",
        )

    if not validate_uuid_format(x_user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    ranger_repo = RangerRepository(db)
    trainer_repo = TrainerRepository(db)

    ranger = ranger_repo.get(x_user_id)
    if ranger:
        return {"id": x_user_id, "role": "ranger", "name": ranger.name}

    trainer = trainer_repo.get(x_user_id)
    if trainer:
        return {"id": x_user_id, "role": "trainer", "name": trainer.name}

    raise HTTPException(status_code=401, detail="Invalid user credentials")


def require_ranger(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "ranger":
        raise HTTPException(status_code=403, detail="Only Rangers can perform this action")
    return current_user
