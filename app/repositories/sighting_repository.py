from datetime import UTC, datetime

from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from app.models import Sighting
from app.repositories.base_repository import BaseRepository


class SightingRepository(BaseRepository[Sighting]):
    def __init__(self, db: Session):
        super().__init__(db, Sighting)

    def get_by_ranger(
        self, ranger_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[Sighting], int]:
        total = self.db.query(Sighting).filter(Sighting.ranger_id == ranger_id).count()
        sightings = (
            self.db.query(Sighting)
            .filter(Sighting.ranger_id == ranger_id)
            .order_by(Sighting.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return sightings, total

    def get_by_region(
        self, region: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[Sighting], int]:
        total = self.db.query(Sighting).filter(Sighting.region == region).count()
        sightings = (
            self.db.query(Sighting)
            .filter(Sighting.region == region)
            .order_by(Sighting.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return sightings, total

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
    ) -> tuple[list[Sighting], int]:
        query = self.db.query(Sighting)

        if pokemon_id is not None:
            query = query.filter(Sighting.pokemon_id == pokemon_id)
        if region is not None:
            query = query.filter(Sighting.region == region)
        if weather is not None:
            query = query.filter(Sighting.weather == weather)
        if time_of_day is not None:
            query = query.filter(Sighting.time_of_day == time_of_day)
        if ranger_id is not None:
            query = query.filter(Sighting.ranger_id == ranger_id)
        if date_from is not None:
            query = query.filter(Sighting.date >= date_from)
        if date_to is not None:
            query = query.filter(Sighting.date <= date_to)
        if is_confirmed is not None:
            query = query.filter(Sighting.is_confirmed == is_confirmed)

        total = query.count()
        sightings = query.order_by(Sighting.date.desc()).offset(skip).limit(limit).all()

        return sightings, total

    def delete_by_ranger(self, sighting_id: str, ranger_id: str) -> bool:
        sighting = (
            self.db.query(Sighting)
            .filter(Sighting.id == sighting_id, Sighting.ranger_id == ranger_id)
            .first()
        )
        if sighting:
            self.db.delete(sighting)
            self.db.commit()
            return True
        return False

    def confirm_sighting_atomic(self, sighting_id: str, confirmer_id: str) -> Sighting:
        result = (
            self.db.query(Sighting)
            .filter(
                Sighting.id == sighting_id,
                Sighting.is_confirmed.is_(False),
                Sighting.ranger_id != confirmer_id,
            )
            .update(
                {
                    "is_confirmed": True,
                    "confirmed_by": confirmer_id,
                    "confirmed_at": datetime.now(UTC),
                },
                synchronize_session=False,
            )
        )

        self.db.commit()

        if result == 0:
            sighting = self.get(sighting_id)
            if not sighting:
                raise ValueError(f"Sighting '{sighting_id}' not found")
            if sighting.is_confirmed:
                raise ValueError(f"Sighting '{sighting_id}' already confirmed")
            if sighting.ranger_id == confirmer_id:
                raise ValueError("Cannot confirm own sighting")

        sighting = self.get(sighting_id)
        if not sighting:
            raise ValueError(f"Sighting '{sighting_id}' not found after confirmation")
        return sighting

    def get_regional_summary_stats(self, region: str) -> dict:
        query_result = (
            self.db.query(
                func.count(Sighting.id).label("total"),
                func.sum(case((Sighting.is_confirmed.is_(True), 1), else_=0)).label("confirmed"),
                func.sum(case((Sighting.is_confirmed.is_(False), 1), else_=0)).label("unconfirmed"),
                func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
            )
            .filter(Sighting.region == region)
            .first()
        )

        if query_result is None:
            return {
                "total": 0,
                "confirmed": 0,
                "unconfirmed": 0,
                "unique_species": 0,
            }

        total = query_result.total if query_result.total is not None else 0  # type: ignore[attr-defined]
        confirmed = query_result.confirmed if query_result.confirmed is not None else 0  # type: ignore[attr-defined]
        unconfirmed = query_result.unconfirmed if query_result.unconfirmed is not None else 0  # type: ignore[attr-defined]
        unique_species = (
            query_result.unique_species if query_result.unique_species is not None else 0
        )  # type: ignore[attr-defined]

        return {
            "total": total,
            "confirmed": confirmed,
            "unconfirmed": unconfirmed,
            "unique_species": unique_species,
        }

    def get_top_pokemon_by_region(self, region: str, limit: int = 5) -> list:
        return (
            self.db.query(Sighting.pokemon_id, func.count(Sighting.id).label("count"))
            .filter(Sighting.region == region)
            .group_by(Sighting.pokemon_id)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )

    def get_top_rangers_by_region(self, region: str, limit: int = 5) -> list:
        return (
            self.db.query(Sighting.ranger_id, func.count(Sighting.id).label("count"))
            .filter(Sighting.region == region)
            .group_by(Sighting.ranger_id)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )

    def get_weather_breakdown(self, region: str) -> dict:
        results = (
            self.db.query(Sighting.weather, func.count(Sighting.id).label("count"))
            .filter(Sighting.region == region)
            .group_by(Sighting.weather)
            .all()
        )

        return {r.weather: r.count for r in results}

    def get_time_of_day_breakdown(self, region: str) -> dict:
        results = (
            self.db.query(Sighting.time_of_day, func.count(Sighting.id).label("count"))
            .filter(Sighting.region == region)
            .group_by(Sighting.time_of_day)
            .all()
        )

        return {r.time_of_day: r.count for r in results}
