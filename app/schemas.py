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
    is_caught: bool | None = None


class PokemonSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type1: str
    type2: str | None
    generation: int


# --- Sighting ---


class ConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sighting_id: str
    confirmed_by: str
    confirmed_by_name: str
    confirmed_at: datetime


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
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    confirmer_name: str | None = None
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


class TopPokemon(BaseModel):
    id: int
    name: str
    count: int


class TopRanger(BaseModel):
    id: str
    name: str
    count: int


class RegionalSummary(BaseModel):
    region: str
    total_sightings: int
    confirmed_sightings: int
    unconfirmed_sightings: int
    unique_species: int
    top_pokemon: list[TopPokemon]
    top_rangers: list[TopRanger]
    weather_breakdown: dict[str, int]
    time_of_day_breakdown: dict[str, int]


class SpeciesSighting(BaseModel):
    id: int
    name: str
    count: int


class RarityTierBreakdown(BaseModel):
    sighting_count: int
    percentage: float
    species: list[SpeciesSighting]


class AnomalySpecies(BaseModel):
    pokemon_id: int
    pokemon_name: str
    rarity_tier: str
    sighting_count: int
    expected_count: float
    deviation: str
    deviation_percentage: float
    is_native: bool


class RegionalAnalysis(BaseModel):
    region: str
    total_sightings: int
    rarity_breakdown: dict[str, RarityTierBreakdown]
    anomalies: list[AnomalySpecies]


LeaderboardSortBy = Literal["total_sightings", "confirmed_sightings", "unique_species"]


class RarestPokemonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pokemon_id: int = Field(..., description="National Pokédex ID")
    pokemon_name: str = Field(..., description="Species name")
    rarity_score: float = Field(..., description="Calculated rarity score")
    is_shiny: bool = Field(..., description="Whether this is a shiny variant")
    date: datetime = Field(..., description="Date of the sighting")


class LeaderboardEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., description="Position in leaderboard (1 = top)")
    ranger_id: str = Field(..., description="UUID of the ranger")
    ranger_name: str = Field(..., description="Display name of the ranger")
    total_sightings: int = Field(..., description="Total number of sightings")
    confirmed_sightings: int = Field(..., description="Number of confirmed sightings")
    unique_species: int = Field(..., description="Number of unique Pokemon species observed")
    rarest_pokemon: RarestPokemonResponse | None = Field(
        None, description="Rarest Pokemon discovered"
    )


class PaginatedLeaderboardResponse(BaseModel):
    results: list[LeaderboardEntryResponse]
    total: int = Field(..., description="Total number of rangers matching filters")
    limit: int = Field(..., description="Maximum number of results per page")
    offset: int = Field(..., description="Number of results skipped")


class TrainerCatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pokemon_id: int
    pokemon_name: str
    caught_at: datetime


class CatchLogResponse(BaseModel):
    trainer_id: str
    trainer_name: str
    catches: list[TrainerCatchResponse]
    total: int


class CatchSummaryResponse(BaseModel):
    trainer_id: str
    trainer_name: str
    total_caught: int
    completion_percentage: float
    caught_by_type: dict[str, int]
    caught_by_generation: dict[int, int]
