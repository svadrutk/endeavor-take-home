from datetime import datetime

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
