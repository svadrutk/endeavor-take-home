from sqlalchemy.orm import Session

from app.models import Ranger
from app.repositories.base_repository import BaseRepository


class RangerRepository(BaseRepository[Ranger]):
    def __init__(self, db: Session):
        super().__init__(db, Ranger)

    def get_by_name(self, name: str) -> Ranger | None:
        return self.db.query(Ranger).filter(Ranger.name == name).first()

    def get_by_email(self, email: str) -> Ranger | None:
        return self.db.query(Ranger).filter(Ranger.email == email).first()
