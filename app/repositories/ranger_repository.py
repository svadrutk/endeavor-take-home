from typing import Optional
from sqlalchemy.orm import Session
import structlog

from app.repositories.base_repository import BaseRepository
from app.models import Ranger


logger = structlog.get_logger()


class RangerRepository(BaseRepository[Ranger]):
    def __init__(self, db: Session):
        super().__init__(db, Ranger)
        self.logger = logger.bind(repository="RangerRepository")

    def get_by_name(self, name: str) -> Optional[Ranger]:
        self.logger.debug("Fetching ranger by name", name=name)
        return self.db.query(Ranger).filter(Ranger.name == name).first()

    def get_by_email(self, email: str) -> Optional[Ranger]:
        self.logger.debug("Fetching ranger by email", email=email)
        return self.db.query(Ranger).filter(Ranger.email == email).first()
