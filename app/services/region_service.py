from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.services.pokemon_service import VALID_REGIONS


class RegionService:
    def __init__(
        self,
        sighting_repo: SightingRepository,
        pokemon_repo: PokemonRepository,
        ranger_repo: RangerRepository,
    ):
        self.sighting_repo = sighting_repo
        self.pokemon_repo = pokemon_repo
        self.ranger_repo = ranger_repo

    def get_regional_summary(self, region_name: str) -> dict:
        region_lower = region_name.lower()
        if region_lower not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{region_name}'. "
                f"Valid regions: {', '.join(sorted(VALID_REGIONS))}"
            )

        # Use the title-cased region name for database queries
        # (sightings are stored with title case, e.g., "Kanto")
        region_title = region_name.title()

        stats = self.sighting_repo.get_regional_summary_stats(region_title)

        top_pokemon_data = self.sighting_repo.get_top_pokemon_by_region(region_title)
        pokemon_ids = [p[0] for p in top_pokemon_data]
        pokemon_list = self.pokemon_repo.get_by_ids(pokemon_ids)
        pokemon_map = {p.id: p.name for p in pokemon_list}

        top_pokemon = [
            {"id": pid, "name": pokemon_map.get(pid, "Unknown"), "count": count}
            for pid, count in top_pokemon_data
        ]

        top_rangers_data = self.sighting_repo.get_top_rangers_by_region(region_title)
        ranger_ids = [r[0] for r in top_rangers_data]
        ranger_list = self.ranger_repo.get_by_ids(ranger_ids)
        ranger_map = {r.id: r.name for r in ranger_list}

        top_rangers = [
            {"id": rid, "name": ranger_map.get(rid, "Unknown"), "count": count}
            for rid, count in top_rangers_data
        ]

        weather_breakdown = self.sighting_repo.get_weather_breakdown(region_title)
        time_of_day_breakdown = self.sighting_repo.get_time_of_day_breakdown(region_title)

        return {
            "region": region_title,
            "total_sightings": stats["total"],
            "confirmed_sightings": stats["confirmed"],
            "unconfirmed_sightings": stats["unconfirmed"],
            "unique_species": stats["unique_species"],
            "top_pokemon": top_pokemon,
            "top_rangers": top_rangers,
            "weather_breakdown": weather_breakdown,
            "time_of_day_breakdown": time_of_day_breakdown,
        }
