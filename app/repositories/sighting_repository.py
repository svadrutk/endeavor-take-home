from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.repositories.base_repository import BaseRepository
from app.models import Sighting


logger = structlog.get_logger()


class SightingRepository(BaseRepository[Sighting]):
    def __init__(self, db: Session):
        super().__init__(db, Sighting)
        self.logger = logger.bind(repository="SightingRepository")

    def get_by_ranger(
        self, ranger_id: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Sighting], int]:
        self.logger.debug(
            "Fetching sightings by ranger", ranger_id=ranger_id, skip=skip, limit=limit
        )
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
    ) -> Tuple[List[Sighting], int]:
        self.logger.debug(
            "Fetching sightings by region", region=region, skip=skip, limit=limit
        )
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
    ) -> Tuple[List[Sighting], int]:
        self.logger.debug(
            "Filtering sightings",
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
        sightings = (
            query.order_by(Sighting.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return sightings, total

    def delete_by_ranger(self, sighting_id: str, ranger_id: str) -> bool:
        self.logger.debug(
            "Deleting sighting by ranger", sighting_id=sighting_id, ranger_id=ranger_id
        )
        sighting = (
            self.db.query(Sighting)
            .filter(Sighting.id == sighting_id, Sighting.ranger_id == ranger_id)
            .first()
        )
        if sighting:
            self.db.delete(sighting)
            self.db.commit()
            self.logger.info("Sighting deleted", sighting_id=sighting_id)
            return True
        self.logger.warning("Sighting not found or not owned by ranger")
        return False
