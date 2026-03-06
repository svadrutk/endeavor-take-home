from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.base_repository import BaseRepository
from app.models import Ranger


class RangerRepository(BaseRepository[Ranger]):
    def __init__(self, db: Session):
        super().__init__(db, Ranger)

    def get_by_name(self, name: str) -> Optional[Ranger]:
        return self.db.query(Ranger).filter(Ranger.name == name).first()

    def get_by_email(self, email: str) -> Optional[Ranger]:
        return self.db.query(Ranger).filter(Ranger.email == email).first()
