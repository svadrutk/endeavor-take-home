from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import generate_uuid


class Pokemon(Base):
    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type1: Mapped[str]
    generation: Mapped[int]
    capture_rate: Mapped[int]
    is_legendary: Mapped[bool] = mapped_column(default=False)
    is_mythical: Mapped[bool] = mapped_column(default=False)
    is_baby: Mapped[bool] = mapped_column(default=False)
    type2: Mapped[str | None] = mapped_column(default=None)
    evolution_chain_id: Mapped[int | None] = mapped_column(default=None)


class Trainer(Base):
    __tablename__ = "trainers"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    id: Mapped[str] = mapped_column(
        primary_key=True,
        init=False,
        default_factory=generate_uuid,
        insert_default=generate_uuid,
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=lambda: datetime.now(UTC),
        insert_default=lambda: datetime.now(UTC),
    )


class Ranger(Base):
    __tablename__ = "rangers"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    specialization: Mapped[str]
    id: Mapped[str] = mapped_column(
        primary_key=True,
        init=False,
        default_factory=generate_uuid,
        insert_default=generate_uuid,
    )
    created_at: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=lambda: datetime.now(UTC),
        insert_default=lambda: datetime.now(UTC),
    )


class Sighting(Base):
    __tablename__ = "sightings"
    __table_args__ = (
        Index("idx_sightings_region", "region"),
        Index("idx_sightings_ranger_id", "ranger_id"),
        Index("idx_sightings_date", "date"),
        Index("idx_sightings_pokemon_id", "pokemon_id"),
        Index("idx_sightings_ranger_date", "ranger_id", "date"),
        Index("idx_sightings_region_date", "region", "date"),
        Index("idx_sightings_is_confirmed", "is_confirmed"),
        {"extend_existing": True},
    )

    pokemon_id: Mapped[int] = mapped_column(ForeignKey("pokemon.id"))
    ranger_id: Mapped[str] = mapped_column(ForeignKey("rangers.id"))
    region: Mapped[str]
    route: Mapped[str]
    date: Mapped[datetime]
    weather: Mapped[str]
    time_of_day: Mapped[str]
    height: Mapped[float]
    weight: Mapped[float]
    is_shiny: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    latitude: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(default=None)
    is_confirmed: Mapped[bool] = mapped_column(default=False)
    id: Mapped[str] = mapped_column(
        primary_key=True,
        init=False,
        default_factory=generate_uuid,
        insert_default=generate_uuid,
    )

    pokemon: Mapped["Pokemon"] = relationship(init=False, lazy="select")
