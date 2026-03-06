from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.services.pokemon_service import REGION_TO_GENERATION, VALID_REGIONS


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

    def _classify_rarity_tier(self, pokemon_data: dict) -> str:
        if pokemon_data["is_mythical"]:
            return "mythical"
        if pokemon_data["is_legendary"]:
            return "legendary"
        if pokemon_data["capture_rate"] < 75:
            return "rare"
        if pokemon_data["capture_rate"] < 150:
            return "uncommon"
        return "common"

    def _detect_anomalies_iqr(self, species_counts: list[dict], region: str) -> list[dict]:
        if len(species_counts) < 2:
            return []

        native_generation = REGION_TO_GENERATION.get(region.lower())

        native_species = [s for s in species_counts if s["generation"] == native_generation]
        non_native_species = [s for s in species_counts if s["generation"] != native_generation]

        anomalies = []

        for group in [native_species, non_native_species]:
            if len(group) < 2:
                continue

            counts = sorted([s["count"] for s in group])
            q1 = counts[len(counts) // 4]
            q3 = counts[3 * len(counts) // 4]
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            expected = (q1 + q3) / 2

            for species in group:
                if species["count"] < lower_bound or species["count"] > upper_bound:
                    deviation = "low" if species["count"] < lower_bound else "high"
                    deviation_percentage = (
                        ((species["count"] - expected) / expected * 100) if expected > 0 else 0
                    )

                    anomalies.append(
                        {
                            "pokemon_id": species["pokemon_id"],
                            "pokemon_name": species["pokemon_name"],
                            "rarity_tier": species["rarity_tier"],
                            "sighting_count": species["count"],
                            "expected_count": expected,
                            "deviation": deviation,
                            "deviation_percentage": deviation_percentage,
                            "is_native": species["generation"] == native_generation,
                        }
                    )

        return anomalies

    def get_regional_summary(self, region_name: str) -> dict:
        region_lower = region_name.lower()
        if region_lower not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{region_name}'. "
                f"Valid regions: {', '.join(sorted(VALID_REGIONS))}"
            )

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

    def get_regional_analysis(self, region_name: str) -> dict:
        region_lower = region_name.lower()
        if region_lower not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{region_name}'. "
                f"Valid regions: {', '.join(sorted(VALID_REGIONS))}"
            )

        region_title = region_name.title()

        sightings_data = self.sighting_repo.get_sightings_by_rarity_tier(region_title)

        if not sightings_data:
            return {
                "region": region_title,
                "total_sightings": 0,
                "rarity_breakdown": {
                    "mythical": {"sighting_count": 0, "percentage": 0.0, "species": []},
                    "legendary": {"sighting_count": 0, "percentage": 0.0, "species": []},
                    "rare": {"sighting_count": 0, "percentage": 0.0, "species": []},
                    "uncommon": {"sighting_count": 0, "percentage": 0.0, "species": []},
                    "common": {"sighting_count": 0, "percentage": 0.0, "species": []},
                },
                "anomalies": [],
            }

        total_sightings = sum(r.total_count for r in sightings_data)

        tier_data = {
            "mythical": [],
            "legendary": [],
            "rare": [],
            "uncommon": [],
            "common": [],
        }

        for result in sightings_data:
            pokemon_data = {
                "is_mythical": result.is_mythical,
                "is_legendary": result.is_legendary,
                "capture_rate": result.capture_rate,
            }
            rarity_tier = self._classify_rarity_tier(pokemon_data)

            tier_data[rarity_tier].append(
                {
                    "pokemon_id": result.pokemon_id,
                    "pokemon_name": result.name,
                    "count": result.total_count,
                    "rarity_tier": rarity_tier,
                    "generation": result.generation,
                }
            )

        rarity_breakdown = {}
        for tier, species_list in tier_data.items():
            tier_count = sum(s["count"] for s in species_list)
            percentage = (tier_count / total_sightings * 100) if total_sightings > 0 else 0.0

            rarity_breakdown[tier] = {
                "sighting_count": tier_count,
                "percentage": round(percentage, 2),
                "species": [
                    {"id": s["pokemon_id"], "name": s["pokemon_name"], "count": s["count"]}
                    for s in sorted(species_list, key=lambda x: x["count"], reverse=True)
                ],
            }

        all_anomalies = []
        for _tier, species_list in tier_data.items():
            if len(species_list) >= 2:
                anomalies = self._detect_anomalies_iqr(species_list, region_title)
                all_anomalies.extend(anomalies)

        return {
            "region": region_title,
            "total_sightings": total_sightings,
            "rarity_breakdown": rarity_breakdown,
            "anomalies": all_anomalies,
        }
