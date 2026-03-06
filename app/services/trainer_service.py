from sqlalchemy.exc import IntegrityError

from app.models import Trainer
from app.repositories.trainer_repository import TrainerRepository
from app.schemas import TrainerCreate


class TrainerService:
    def __init__(self, trainer_repo: TrainerRepository):
        self.trainer_repo = trainer_repo

    def create_trainer(self, trainer_data: TrainerCreate) -> Trainer:
        existing_name = self.trainer_repo.get_by_name(trainer_data.name)
        if existing_name:
            raise ValueError(f"Trainer with name '{trainer_data.name}' already exists")

        existing_email = self.trainer_repo.get_by_email(trainer_data.email)
        if existing_email:
            raise ValueError(f"Trainer with email '{trainer_data.email}' already exists")

        try:
            trainer = self.trainer_repo.create(
                {
                    "name": trainer_data.name,
                    "email": trainer_data.email,
                }
            )
            return trainer
        except IntegrityError:
            raise ValueError("Trainer with this name or email already exists") from None

    def get_trainer(self, trainer_id: str) -> Trainer | None:
        return self.trainer_repo.get(trainer_id)

    def lookup_user_by_name(self, name: str) -> dict | None:
        trainer = self.trainer_repo.get_by_name(name)
        if trainer:
            return {"id": trainer.id, "name": trainer.name, "role": "trainer"}
        return None
