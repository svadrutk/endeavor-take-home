from typing import List, Optional
from sqlalchemy.orm import Session
import structlog

from app.repositories.base_repository import BaseRepository
from app.models import Pokemon


logger = structlog.get_logger()


class PokemonRepository(BaseRepository[Pokemon]):
    def __init__(self, db: Session):
        super().__init__(db, Pokemon)
        self.logger = logger.bind(repository="PokemonRepository")

    def get_by_generation(self, generation: int) -> List[Pokemon]:
        self.logger.debug("Fetching pokemon by generation", generation=generation)
        return self.db.query(Pokemon).filter(Pokemon.generation == generation).all()

    def search_by_name(self, name: str, skip: int = 0, limit: int = 100) -> List[Pokemon]:
        self.logger.debug("Searching pokemon by name", name=name, skip=skip, limit=limit)
        escaped_name = name.replace("%", "\\%").replace("_", "\\_")
        return (
            self.db.query(Pokemon)
            .filter(Pokemon.name.ilike(f"%{escaped_name}%", escape="\\"))
            .order_by(Pokemon.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_name_search(self, name: str) -> int:
        escaped_name = name.replace("%", "\\%").replace("_", "\\_")
        return (
            self.db.query(Pokemon)
            .filter(Pokemon.name.ilike(f"%{escaped_name}%", escape="\\"))
            .count()
        )
