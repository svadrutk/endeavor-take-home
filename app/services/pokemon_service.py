from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.repositories.pokemon_repository import PokemonRepository
from app.models import Pokemon


REGION_TO_GENERATION = {
    "kanto": 1,
    "johto": 2,
    "hoenn": 3,
    "sinnoh": 4,
}

VALID_REGIONS = {"kanto", "johto", "hoenn", "sinnoh"}
VALID_GENERATIONS = {1, 2, 3, 4}


class PokemonService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PokemonRepository(db)

    def get_pokemon(self, pokemon_id: int) -> Optional[Pokemon]:
        return self.repository.get(pokemon_id)

    def list_pokemon(self, skip: int = 0, limit: int = 100) -> Tuple[List[Pokemon], int]:
        total = self.repository.count()
        pokemon_list = self.repository.get_multi(skip=skip, limit=limit, order_by=Pokemon.id)
        return pokemon_list, total

    def search_pokemon(self, name: str, skip: int = 0, limit: int = 100) -> Tuple[List[Pokemon], int]:
        total = self.repository.count_by_name_search(name)
        pokemon_list = self.repository.search_by_name(name, skip=skip, limit=limit)
        return pokemon_list, total

    def get_pokemon_by_region(self, region_or_generation: str) -> Tuple[List[Pokemon], int]:
        region_lower = region_or_generation.lower()
        generation = REGION_TO_GENERATION.get(region_lower)
        
        if generation is None:
            try:
                generation = int(region_or_generation)
                if generation not in VALID_GENERATIONS:
                    raise ValueError(
                        f"Invalid generation: {generation}. "
                        f"Valid generations are: {', '.join(map(str, sorted(VALID_GENERATIONS)))} "
                        f"(Kanto=1, Johto=2, Hoenn=3, Sinnoh=4)"
                    )
            except ValueError as e:
                if "Invalid generation" in str(e):
                    raise
                raise ValueError(
                    f"Invalid region or generation: '{region_or_generation}'. "
                    f"Valid regions: {', '.join(sorted(VALID_REGIONS))}. "
                    f"Valid generations: {', '.join(map(str, sorted(VALID_GENERATIONS)))}"
                )
        
        pokemon_list = self.repository.get_by_generation(generation)
        return pokemon_list, len(pokemon_list)
