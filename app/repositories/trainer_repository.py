from sqlalchemy.orm import Session

from app.models import Trainer
from app.repositories.base_repository import BaseRepository


class TrainerRepository(BaseRepository[Trainer]):
    def __init__(self, db: Session):
        super().__init__(db, Trainer)

    def get_by_name(self, name: str) -> Trainer | None:
        return self.db.query(Trainer).filter(Trainer.name == name).first()

    def get_by_email(self, email: str) -> Trainer | None:
        return self.db.query(Trainer).filter(Trainer.email == email).first()
