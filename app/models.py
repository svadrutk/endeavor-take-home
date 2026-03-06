from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import generate_uuid


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    def can_transition_to(self, next_status: "CampaignStatus") -> bool:
        valid_transitions = {
            CampaignStatus.DRAFT: {CampaignStatus.ACTIVE},
            CampaignStatus.ACTIVE: {CampaignStatus.COMPLETED},
            CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
            CampaignStatus.ARCHIVED: set(),
        }
        return next_status in valid_transitions.get(self, set())


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


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("idx_campaigns_status", "status"),
        Index("idx_campaigns_region", "region"),
        Index("idx_campaigns_dates", "start_date", "end_date"),
    )

    name: Mapped[str] = mapped_column(String(255))
    region: Mapped[str]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default=CampaignStatus.DRAFT)
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
    updated_at: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=lambda: datetime.now(UTC),
        insert_default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
        Index("idx_sightings_campaign_id", "campaign_id"),
        Index("idx_sightings_campaign_date", "campaign_id", "date"),
        Index("idx_sightings_confirmed_by", "confirmed_by"),
        Index("idx_sightings_confirmation_status", "is_confirmed", "confirmed_at"),
        CheckConstraint(
            "(is_confirmed = FALSE) OR (confirmed_by IS NOT NULL)",
            name="ck_sighting_confirmation_integrity",
        ),
        CheckConstraint(
            "(is_confirmed = FALSE) OR (confirmed_at IS NOT NULL)",
            name="ck_sighting_confirmation_timestamp",
        ),
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
    confirmed_by: Mapped[str | None] = mapped_column(
        ForeignKey("rangers.id", ondelete="SET NULL"), default=None, nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(default=None)
    campaign_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), default=None
    )
    id: Mapped[str] = mapped_column(
        primary_key=True,
        init=False,
        default_factory=generate_uuid,
        insert_default=generate_uuid,
    )

    pokemon: Mapped["Pokemon"] = relationship("Pokemon", init=False, lazy="select")
    ranger: Mapped["Ranger"] = relationship(
        "Ranger", foreign_keys=[ranger_id], init=False, lazy="select"
    )
    confirming_ranger: Mapped["Ranger | None"] = relationship(
        "Ranger", foreign_keys=[confirmed_by], init=False, lazy="select"
    )
