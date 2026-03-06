from sqlalchemy.exc import IntegrityError

from app.models import Pokemon, Trainer, TrainerCatch
from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.trainer_catch_repository import TrainerCatchRepository
from app.repositories.trainer_repository import TrainerRepository
from app.schemas import TrainerCreate


class TrainerService:
    def __init__(
        self,
        trainer_repo: TrainerRepository,
        trainer_catch_repo: TrainerCatchRepository | None = None,
        pokemon_repo: PokemonRepository | None = None,
    ):
        self.trainer_repo = trainer_repo
        self.trainer_catch_repo = trainer_catch_repo
        self.pokemon_repo = pokemon_repo

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

    def mark_pokemon_caught(
        self, trainer_id: str, pokemon_id: int, current_user_id: str
    ) -> tuple[TrainerCatch, Pokemon]:
        if trainer_id != current_user_id:
            raise ValueError(
                "Permission denied: cannot modify another trainer's catch log. You can only modify your own catch log."
            )

        if not self.trainer_catch_repo or not self.pokemon_repo:
            raise ValueError("Repository not initialized")

        existing = self.trainer_catch_repo.get_by_trainer_and_pokemon(trainer_id, pokemon_id)
        if existing:
            raise ValueError(f"Pokemon with ID {pokemon_id} is already marked as caught")

        pokemon = self.pokemon_repo.get(pokemon_id)
        if not pokemon:
            raise ValueError(f"Pokemon with ID {pokemon_id} not found")

        try:
            catch = self.trainer_catch_repo.create(
                {"trainer_id": trainer_id, "pokemon_id": pokemon_id}
            )
            return catch, pokemon
        except IntegrityError:
            raise ValueError("Pokemon already marked as caught") from None

    def unmark_pokemon_caught(self, trainer_id: str, pokemon_id: int, current_user_id: str) -> bool:
        if trainer_id != current_user_id:
            raise ValueError(
                "Permission denied: cannot modify another trainer's catch log. You can only modify your own catch log."
            )

        if not self.trainer_catch_repo:
            raise ValueError("Repository not initialized")

        pokemon = self.pokemon_repo.get(pokemon_id) if self.pokemon_repo else None
        if not pokemon:
            raise ValueError(f"Pokemon with ID {pokemon_id} not found")

        deleted = self.trainer_catch_repo.delete_by_trainer_and_pokemon(trainer_id, pokemon_id)
        if not deleted:
            raise ValueError(f"Pokemon with ID {pokemon_id} is not in your catch log")

        return True

    def has_caught_pokemon(self, trainer_id: str, pokemon_id: int) -> bool:
        if not self.trainer_catch_repo:
            return False

        catch = self.trainer_catch_repo.get_by_trainer_and_pokemon(trainer_id, pokemon_id)
        return catch is not None

    def get_catch_log(self, trainer_id: str, skip: int = 0, limit: int = 100) -> list[TrainerCatch]:
        if not self.trainer_catch_repo:
            return []

        return self.trainer_catch_repo.get_catch_log(trainer_id, skip, limit)

    def get_catch_summary(self, trainer_id: str) -> dict:
        if not self.trainer_catch_repo:
            return {
                "total_caught": 0,
                "completion_percentage": 0.0,
                "caught_by_type": {},
                "caught_by_generation": {},
            }

        total_caught = self.trainer_catch_repo.count_by_trainer(trainer_id)

        caught_by_type = self.trainer_catch_repo.get_catches_by_type(trainer_id)
        caught_by_generation = self.trainer_catch_repo.get_catches_by_generation(trainer_id)

        return {
            "total_caught": total_caught,
            "completion_percentage": round((total_caught / 493) * 100, 2),
            "caught_by_type": {row.type1: row.count for row in caught_by_type},
            "caught_by_generation": {row.generation: row.count for row in caught_by_generation},
        }
