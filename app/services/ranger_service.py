from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Ranger
from app.repositories.ranger_repository import RangerRepository
from app.schemas import RangerCreate


class RangerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = RangerRepository(db)

    def create_ranger(self, ranger_data: RangerCreate) -> Ranger:
        existing_name = self.repository.get_by_name(ranger_data.name)
        if existing_name:
            raise ValueError(f"Ranger with name '{ranger_data.name}' already exists")

        existing_email = self.repository.get_by_email(ranger_data.email)
        if existing_email:
            raise ValueError(f"Ranger with email '{ranger_data.email}' already exists")

        try:
            ranger = self.repository.create(
                {
                    "name": ranger_data.name,
                    "email": ranger_data.email,
                    "specialization": ranger_data.specialization,
                }
            )
            return ranger
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Ranger with this name or email already exists") from None

    def get_ranger(self, ranger_id: str) -> Ranger | None:
        return self.repository.get(ranger_id)

    def validate_ranger(self, ranger_id: str) -> Ranger:
        ranger = self.get_ranger(ranger_id)
        if not ranger:
            raise ValueError(f"Ranger with ID '{ranger_id}' not found")
        return ranger

    def lookup_user_by_name(self, name: str) -> dict | None:
        ranger = self.repository.get_by_name(name)
        if ranger:
            return {"id": ranger.id, "name": ranger.name, "role": "ranger"}
        return None
