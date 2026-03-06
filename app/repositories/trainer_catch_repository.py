from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Pokemon, TrainerCatch
from app.repositories.base_repository import BaseRepository


class TrainerCatchRepository(BaseRepository[TrainerCatch]):
    def __init__(self, db: Session):
        super().__init__(db, TrainerCatch)

    def get(self, id) -> TrainerCatch | None:
        raise NotImplementedError("Use get_by_trainer_and_pokemon for TrainerCatch")

    def get_by_trainer_and_pokemon(self, trainer_id: str, pokemon_id: int) -> TrainerCatch | None:
        return (
            self.db.query(TrainerCatch)
            .filter(
                TrainerCatch.trainer_id == trainer_id,
                TrainerCatch.pokemon_id == pokemon_id,
            )
            .first()
        )

    def create(self, obj_in: dict) -> TrainerCatch:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        try:
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            self.db.rollback()
            raise

    def get_catch_log(self, trainer_id: str, skip: int = 0, limit: int = 100) -> list[TrainerCatch]:
        return (
            self.db.query(TrainerCatch)
            .options(joinedload(TrainerCatch.pokemon), joinedload(TrainerCatch.trainer))
            .filter(TrainerCatch.trainer_id == trainer_id)
            .order_by(TrainerCatch.caught_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_trainer(self, trainer_id: str) -> int:
        return (
            self.db.query(func.count(TrainerCatch.pokemon_id))
            .filter(TrainerCatch.trainer_id == trainer_id)
            .scalar()
        )

    def get_catches_by_type(self, trainer_id: str) -> list:
        return (
            self.db.query(Pokemon.type1, func.count(TrainerCatch.pokemon_id).label("count"))
            .join(TrainerCatch, Pokemon.id == TrainerCatch.pokemon_id)
            .filter(TrainerCatch.trainer_id == trainer_id)
            .group_by(Pokemon.type1)
            .all()
        )

    def get_catches_by_generation(self, trainer_id: str) -> list:
        return (
            self.db.query(Pokemon.generation, func.count(TrainerCatch.pokemon_id).label("count"))
            .join(TrainerCatch, Pokemon.id == TrainerCatch.pokemon_id)
            .filter(TrainerCatch.trainer_id == trainer_id)
            .group_by(Pokemon.generation)
            .all()
        )

    def delete_by_trainer_and_pokemon(self, trainer_id: str, pokemon_id: int) -> bool:
        catch = self.get_by_trainer_and_pokemon(trainer_id, pokemon_id)
        if catch:
            self.db.delete(catch)
            self.db.commit()
            return True
        return False
