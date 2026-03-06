from typing import Optional, Tuple, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.sighting_repository import SightingRepository
from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository
from app.models import Sighting, Pokemon, Ranger
from app.schemas import SightingCreate


class SightingService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SightingRepository(db)
        self.pokemon_repository = PokemonRepository(db)
        self.ranger_repository = RangerRepository(db)

    def create_sighting(
        self, sighting_data: SightingCreate, ranger_id: str
    ) -> Tuple[Sighting, Pokemon, Ranger]:
        ranger = self.ranger_repository.get(ranger_id)
        if not ranger:
            raise ValueError(f"Ranger with ID '{ranger_id}' not found. Only rangers can log sightings.")
        
        pokemon = self.pokemon_repository.get(sighting_data.pokemon_id)
        if not pokemon:
            raise ValueError(f"Pokemon with ID '{sighting_data.pokemon_id}' not found")
        
        sighting = self.repository.create({
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
        })
        
        return sighting, pokemon, ranger

    def get_sighting(self, sighting_id: str) -> Optional[Tuple[Sighting, Optional[Pokemon], Optional[Ranger]]]:
        sighting = self.repository.get(sighting_id)
        if not sighting:
            return None
        
        pokemon = self.pokemon_repository.get(sighting.pokemon_id)
        ranger = self.ranger_repository.get(sighting.ranger_id)
        
        return sighting, pokemon, ranger

    def get_ranger_sightings(
        self, ranger_id: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Tuple[Sighting, Pokemon, Ranger]], int]:
        ranger = self.ranger_repository.get(ranger_id)
        if not ranger:
            raise ValueError(f"Ranger with ID '{ranger_id}' not found")
        
        sightings, total = self.repository.get_by_ranger(ranger_id, skip=skip, limit=limit)
        
        result = []
        for sighting in sightings:
            pokemon = self.pokemon_repository.get(sighting.pokemon_id)
            result.append((sighting, pokemon, ranger))
        
        return result, total

    def delete_sighting(self, sighting_id: str, ranger_id: str) -> bool:
        sighting = self.repository.get(sighting_id)
        if not sighting:
            raise ValueError(f"Sighting with ID '{sighting_id}' not found")
        
        if sighting.ranger_id != ranger_id:
            raise ValueError(
                f"Permission denied: This sighting belongs to ranger '{sighting.ranger_id}', "
                f"not '{ranger_id}'. You can only delete your own sightings."
            )
        
        return self.repository.delete(sighting_id)

    def filter_sightings(
        self,
        pokemon_id: Optional[int] = None,
        region: Optional[str] = None,
        weather: Optional[str] = None,
        time_of_day: Optional[str] = None,
        ranger_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_confirmed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Tuple[Sighting, Optional[Pokemon], Optional[Ranger]]], int]:
        sightings, total = self.repository.filter_sightings(
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
            pokemon = self.pokemon_repository.get(sighting.pokemon_id)
            ranger = self.ranger_repository.get(sighting.ranger_id)
            result.append((sighting, pokemon, ranger))
        
        return result, total
