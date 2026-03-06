from datetime import datetime
from typing import TYPE_CHECKING

from app.models import Pokemon, Ranger, Sighting
from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.schemas import SightingCreate

if TYPE_CHECKING:
    from app.services.campaign_service import CampaignService


class SightingService:
    def __init__(
        self,
        sighting_repo: SightingRepository,
        pokemon_repo: PokemonRepository,
        ranger_repo: RangerRepository,
        campaign_service: "CampaignService | None" = None,
    ):
        self.sighting_repo = sighting_repo
        self.pokemon_repo = pokemon_repo
        self.ranger_repo = ranger_repo
        self.campaign_service = campaign_service

    def create_sighting(
        self, sighting_data: SightingCreate, ranger_id: str
    ) -> tuple[Sighting, Pokemon, Ranger]:
        ranger = self.ranger_repo.get(ranger_id)
        if not ranger:
            raise ValueError(
                f"Ranger with ID '{ranger_id}' not found. Only rangers can log sightings."
            )

        pokemon = self.pokemon_repo.get(sighting_data.pokemon_id)
        if not pokemon:
            raise ValueError(f"Pokemon with ID '{sighting_data.pokemon_id}' not found")

        if sighting_data.campaign_id and self.campaign_service:
            self.campaign_service.validate_sighting_campaign(sighting_data.campaign_id)

        sighting = self.sighting_repo.create(
            {
                "pokemon_id": sighting_data.pokemon_id,
                "ranger_id": ranger_id,
                "region": sighting_data.region,
                "route": sighting_data.route,
                "date": sighting_data.date,
                "weather": sighting_data.weather,
                "time_of_day": sighting_data.time_of_day,
                "height": sighting_data.height,
                "weight": sighting_data.weight,
                "is_shiny": sighting_data.is_shiny,
                "notes": sighting_data.notes,
                "latitude": sighting_data.latitude,
                "longitude": sighting_data.longitude,
                "campaign_id": sighting_data.campaign_id,
            }
        )

        return sighting, pokemon, ranger

    def get_sighting(
        self, sighting_id: str
    ) -> tuple[Sighting, Pokemon | None, Ranger | None] | None:
        sighting = self.sighting_repo.get(sighting_id)
        if not sighting:
            return None

        pokemon = self.pokemon_repo.get(sighting.pokemon_id)
        ranger = self.ranger_repo.get(sighting.ranger_id)

        return sighting, pokemon, ranger

    def get_ranger_sightings(
        self, ranger_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[tuple[Sighting, Pokemon, Ranger]], int]:
        ranger = self.ranger_repo.get(ranger_id)
        if not ranger:
            raise ValueError(f"Ranger with ID '{ranger_id}' not found")

        sightings, total = self.sighting_repo.get_by_ranger(ranger_id, skip=skip, limit=limit)

        result = []
        for sighting in sightings:
            pokemon = self.pokemon_repo.get(sighting.pokemon_id)
            result.append((sighting, pokemon, ranger))

        return result, total

    def delete_sighting(self, sighting_id: str, ranger_id: str) -> bool:
        sighting = self.sighting_repo.get(sighting_id)
        if not sighting:
            raise ValueError(f"Sighting with ID '{sighting_id}' not found")

        if self.campaign_service:
            self.campaign_service.check_sighting_lock(sighting)

        if sighting.ranger_id != ranger_id:
            raise ValueError(
                f"Permission denied: This sighting belongs to ranger '{sighting.ranger_id}', "
                f"not '{ranger_id}'. You can only delete your own sightings."
            )

        return self.sighting_repo.delete(sighting_id)

    def filter_sightings(
        self,
        pokemon_id: int | None = None,
        region: str | None = None,
        weather: str | None = None,
        time_of_day: str | None = None,
        ranger_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        is_confirmed: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[tuple[Sighting, Pokemon | None, Ranger | None]], int]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be before or equal to date_to")

        sightings, total = self.sighting_repo.filter_sightings(
            pokemon_id=pokemon_id,
            region=region,
            weather=weather,
            time_of_day=time_of_day,
            ranger_id=ranger_id,
            date_from=date_from,
            date_to=date_to,
            is_confirmed=is_confirmed,
            skip=skip,
            limit=limit,
        )

        result = []
        for sighting in sightings:
            pokemon = self.pokemon_repo.get(sighting.pokemon_id)
            ranger = self.ranger_repo.get(sighting.ranger_id)
            result.append((sighting, pokemon, ranger))

        return result, total

    def confirm_sighting(
        self, sighting_id: str, confirming_ranger_id: str
    ) -> tuple[Sighting, Pokemon, Ranger]:
        confirmer = self.ranger_repo.get(confirming_ranger_id)
        if not confirmer:
            raise ValueError(
                f"User '{confirming_ranger_id}' is not a Ranger. Only Rangers can confirm sightings."
            )

        sighting = self.sighting_repo.get(sighting_id)
        if not sighting:
            raise ValueError(f"Sighting with ID '{sighting_id}' not found")

        if sighting.ranger_id == confirming_ranger_id:
            raise ValueError(
                f"Permission denied: You cannot confirm your own sighting. "
                f"Sighting belongs to ranger '{sighting.ranger_id}'."
            )

        if sighting.is_confirmed:
            raise ValueError(
                f"Sighting '{sighting_id}' is already confirmed. "
                "Each sighting can only be confirmed once."
            )

        sighting = self.sighting_repo.confirm_sighting_atomic(sighting_id, confirming_ranger_id)

        pokemon = self.pokemon_repo.get(sighting.pokemon_id)
        if not pokemon:
            raise ValueError(f"Pokemon with ID '{sighting.pokemon_id}' not found")

        ranger = self.ranger_repo.get(sighting.ranger_id)
        if not ranger:
            raise ValueError(f"Ranger with ID '{sighting.ranger_id}' not found")

        return sighting, pokemon, ranger

    def get_confirmation(self, sighting_id: str) -> dict | None:
        sighting = self.sighting_repo.get(sighting_id)
        if not sighting:
            raise ValueError(f"Sighting with ID '{sighting_id}' not found")

        if not sighting.is_confirmed:
            return None

        confirmer = self.ranger_repo.get(sighting.confirmed_by)

        return {
            "sighting_id": sighting_id,
            "confirmed_by": sighting.confirmed_by,
            "confirmed_by_name": confirmer.name if confirmer else None,
            "confirmed_at": sighting.confirmed_at,
        }
