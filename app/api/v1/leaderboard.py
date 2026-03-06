from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_leaderboard_service
from app.schemas import (
    LeaderboardEntryResponse,
    LeaderboardSortBy,
    PaginatedLeaderboardResponse,
    RarestPokemonResponse,
)
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/", response_model=PaginatedLeaderboardResponse)
def get_leaderboard(
    request: Request,
    region: str | None = Query(None, description="Filter by region name"),
    date_from: datetime | None = Query(None, description="Filter from date (inclusive)"),
    date_to: datetime | None = Query(None, description="Filter to date (inclusive)"),
    campaign_id: str | None = Query(None, description="Filter by campaign ID"),
    sort_by: LeaderboardSortBy = Query(
        "total_sightings",
        description="Sort field (total_sightings, confirmed_sightings, unique_species)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, le=10000, description="Number of results to skip"),
    service: LeaderboardService = Depends(get_leaderboard_service),
):
    """
    Get paginated leaderboard of rangers.

    Supports filtering by:
    - region: Region name (e.g., "Kanto", "Johto")
    - date_from: Start of date range (inclusive)
    - date_to: End of date range (inclusive)
    - campaign_id: Campaign UUID

    Supports sorting by:
    - total_sightings (default)
    - confirmed_sightings
    - unique_species

    Returns paginated results with total count.
    """
    try:
        results, total = service.get_leaderboard(
            region=region,
            date_from=date_from,
            date_to=date_to,
            campaign_id=campaign_id,
            sort_by=sort_by,
            skip=offset,
            limit=limit,
        )

        formatted_results = []
        for entry in results:
            rarest_pokemon = None
            if entry.get("rarest_pokemon"):
                rarest_pokemon = RarestPokemonResponse(**entry["rarest_pokemon"])

            formatted_results.append(
                LeaderboardEntryResponse(
                    rank=entry["rank"],
                    ranger_id=entry["ranger_id"],
                    ranger_name=entry["ranger_name"],
                    total_sightings=entry["total_sightings"],
                    confirmed_sightings=entry["confirmed_sightings"],
                    unique_species=entry["unique_species"],
                    rarest_pokemon=rarest_pokemon,
                )
            )

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["leaderboard"] = {
                "total_rangers": total,
                "filters": {
                    "region": region,
                    "date_from": str(date_from) if date_from else None,
                    "date_to": str(date_to) if date_to else None,
                    "campaign_id": campaign_id,
                    "sort_by": sort_by,
                },
            }

        return PaginatedLeaderboardResponse(
            results=formatted_results,
            total=total,
            limit=limit,
            offset=offset,
        )

    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e),
            }
        raise HTTPException(status_code=400, detail=str(e)) from None
