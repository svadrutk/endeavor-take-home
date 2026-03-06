from app.models import Pokemon
from app.repositories.pokemon_repository import PokemonRepository

REGION_TO_GENERATION = {
    "kanto": 1,
    "johto": 2,
    "hoenn": 3,
    "sinnoh": 4,
}

VALID_REGIONS = {"kanto", "johto", "hoenn", "sinnoh"}
VALID_GENERATIONS = {1, 2, 3, 4}


class PokemonService:
    def __init__(self, pokemon_repo: PokemonRepository):
        self.pokemon_repo = pokemon_repo

    def get_pokemon(self, pokemon_id: int) -> Pokemon | None:
        return self.pokemon_repo.get(pokemon_id)

    def list_pokemon(self, skip: int = 0, limit: int = 100) -> tuple[list[Pokemon], int]:
        total = self.pokemon_repo.count()
        pokemon_list = self.pokemon_repo.get_multi(skip=skip, limit=limit, order_by=Pokemon.id)
        return pokemon_list, total

    def search_pokemon(
        self, name: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[Pokemon], int]:
        total = self.pokemon_repo.count_by_name_search(name)
        pokemon_list = self.pokemon_repo.search_by_name(name, skip=skip, limit=limit)
        return pokemon_list, total

    def get_pokemon_by_region(self, region_or_generation: str) -> tuple[list[Pokemon], int]:
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
                ) from None

        pokemon_list = self.pokemon_repo.get_by_generation(generation)
        return pokemon_list, len(pokemon_list)
