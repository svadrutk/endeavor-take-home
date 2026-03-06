from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- Trainer ---


class TrainerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr


class TrainerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    created_at: datetime


# --- Ranger ---


class RangerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    specialization: str = Field(..., min_length=1)


class RangerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    specialization: str
    created_at: datetime


# --- User Lookup ---


class UserLookupResponse(BaseModel):
    id: str
    name: str
    role: Literal["trainer", "ranger"]


# --- Pokemon ---


class PokemonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type1: str
    type2: str | None
    generation: int
    is_legendary: bool
    is_mythical: bool
    is_baby: bool
    capture_rate: int
    evolution_chain_id: int | None


class PokemonSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type1: str
    type2: str | None
    generation: int


# --- Sighting ---


class SightingCreate(BaseModel):
    pokemon_id: int
    region: str
    route: str
    date: datetime
    weather: Literal["sunny", "rainy", "snowy", "sandstorm", "foggy", "clear"]
    time_of_day: Literal["morning", "day", "night"]
    height: float
    weight: float
    is_shiny: bool = False
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    campaign_id: str | None = None


class SightingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pokemon_id: int
    ranger_id: str
    region: str
    route: str
    date: datetime
    weather: str
    time_of_day: str
    height: float
    weight: float
    is_shiny: bool
    notes: str | None
    is_confirmed: bool
    campaign_id: str | None = None
    pokemon_name: str | None = None
    ranger_name: str | None = None


# --- Generic ---


class MessageResponse(BaseModel):
    detail: str


# --- Pagination ---


class PaginatedSightingResponse(BaseModel):
    results: list[SightingResponse]
    total: int
    limit: int
    offset: int


class PaginatedPokemonResponse(BaseModel):
    results: list[PokemonResponse]
    total: int
    limit: int
    offset: int


class PaginatedPokemonSearchResult(BaseModel):
    results: list[PokemonSearchResult]
    total: int
    limit: int
    offset: int


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    region: str = Field(..., min_length=1)
    start_date: datetime
    end_date: datetime


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    region: str
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime


class CampaignSummary(BaseModel):
    campaign_id: str
    campaign_name: str
    total_sightings: int
    unique_species: int
    contributing_rangers: list[dict[str, str | int]]
    observation_date_range: dict[str, datetime | None]
