from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Trainer
from app.repositories.trainer_repository import TrainerRepository
from app.schemas import TrainerCreate


class TrainerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TrainerRepository(db)

    def create_trainer(self, trainer_data: TrainerCreate) -> Trainer:
        existing_name = self.repository.get_by_name(trainer_data.name)
        if existing_name:
            raise ValueError(f"Trainer with name '{trainer_data.name}' already exists")

        existing_email = self.repository.get_by_email(trainer_data.email)
        if existing_email:
            raise ValueError(f"Trainer with email '{trainer_data.email}' already exists")

        try:
            trainer = self.repository.create(
                {
                    "name": trainer_data.name,
                    "email": trainer_data.email,
                }
            )
            return trainer
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Trainer with this name or email already exists") from None

    def get_trainer(self, trainer_id: str) -> Trainer | None:
        return self.repository.get(trainer_id)

    def lookup_user_by_name(self, name: str) -> dict | None:
        trainer = self.repository.get_by_name(name)
        if trainer:
            return {"id": trainer.id, "name": trainer.name, "role": "trainer"}
        return None
