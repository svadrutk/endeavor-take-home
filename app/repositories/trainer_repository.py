from typing import Optional
from sqlalchemy.orm import Session
import structlog

from app.repositories.base_repository import BaseRepository
from app.models import Trainer


logger = structlog.get_logger()


class TrainerRepository(BaseRepository[Trainer]):
    def __init__(self, db: Session):
        super().__init__(db, Trainer)
        self.logger = logger.bind(repository="TrainerRepository")

    def get_by_name(self, name: str) -> Optional[Trainer]:
        self.logger.debug("Fetching trainer by name", name=name)
        return self.db.query(Trainer).filter(Trainer.name == name).first()

    def get_by_email(self, email: str) -> Optional[Trainer]:
        self.logger.debug("Fetching trainer by email", email=email)
        return self.db.query(Trainer).filter(Trainer.email == email).first()
