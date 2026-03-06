from datetime import UTC, datetime

from app.repositories.ranger_repository import RangerRepository
from app.repositories.sighting_repository import SightingRepository
from app.services.pokemon_service import VALID_REGIONS


class LeaderboardService:
    def __init__(
        self,
        sighting_repo: SightingRepository,
        ranger_repo: RangerRepository,
    ):
        self.sighting_repo = sighting_repo
        self.ranger_repo = ranger_repo

    def get_leaderboard(
        self,
        region: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        campaign_id: str | None = None,
        sort_by: str = "total_sightings",
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        self._validate_filters(region, date_from, date_to, campaign_id, skip, limit)

        region_title = region.title() if region else None

        raw_stats, total = self.sighting_repo.get_leaderboard_stats(
            region=region_title,
            date_from=date_from,
            date_to=date_to,
            campaign_id=campaign_id,
            sort_by=sort_by,
            skip=skip,
            limit=limit,
        )

        ranger_ids = [stat.ranger_id for stat in raw_stats]
        rangers = self.ranger_repo.get_by_ids(ranger_ids)
        ranger_map = {r.id: r.name for r in rangers}

        rarest_map = self.sighting_repo.get_rarest_pokemon_for_rangers(
            ranger_ids=ranger_ids,
            region=region_title,
            date_from=date_from,
            date_to=date_to,
            campaign_id=campaign_id,
        )

        results = []
        for idx, stat in enumerate(raw_stats, start=skip + 1):
            results.append(
                {
                    "rank": idx,
                    "ranger_id": stat.ranger_id,
                    "ranger_name": ranger_map.get(stat.ranger_id, "Unknown"),
                    "total_sightings": stat.total_sightings,
                    "confirmed_sightings": stat.confirmed_sightings,
                    "unique_species": stat.unique_species,
                    "rarest_pokemon": rarest_map.get(stat.ranger_id),
                }
            )

        return results, total

    def _validate_filters(
        self,
        region: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        campaign_id: str | None,
        skip: int,
        limit: int,
    ):
        if region and region.lower() not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{region}'. Valid regions: {', '.join(sorted(VALID_REGIONS))}"
            )

        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be before or equal to date_to")

        if date_from:
            now = datetime.now(UTC)
            if date_from.tzinfo is None:
                date_from_aware = date_from.replace(tzinfo=UTC)
            else:
                date_from_aware = date_from
            if date_from_aware > now:
                raise ValueError("date_from cannot be in the future")

        if limit > 200:
            raise ValueError("Maximum limit is 200")

        if skip > 10000:
            raise ValueError("Maximum offset is 10,000")
