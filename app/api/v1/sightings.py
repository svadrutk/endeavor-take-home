from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.api.deps import get_sighting_service
from app.schemas import MessageResponse, PaginatedSightingResponse, SightingCreate, SightingResponse
from app.services import SightingService

router = APIRouter(prefix="/sightings", tags=["sightings"])


@router.get("/", response_model=PaginatedSightingResponse)
def list_sightings(
    request: Request,
    service: SightingService = Depends(get_sighting_service),
    pokemon_id: int | None = Query(None, description="Filter by Pokemon species ID"),
    region: str | None = Query(None, description="Filter by region name"),
    weather: str | None = Query(None, description="Filter by weather condition"),
    time_of_day: str | None = Query(None, description="Filter by time of day"),
    ranger_id: str | None = Query(None, description="Filter by Ranger UUID"),
    date_from: datetime | None = Query(
        None, description="Filter sightings from this date (inclusive)"
    ),
    date_to: datetime | None = Query(None, description="Filter sightings to this date (inclusive)"),
    is_confirmed: bool | None = Query(None, description="Filter by confirmation status"),
    limit: int = Query(50, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List sightings with optional filters and pagination.

    Supports filtering by:
    - pokemon_id: Pokemon species ID
    - region: Region name (e.g., "Kanto", "Johto")
    - weather: Weather condition (sunny, rainy, snowy, sandstorm, foggy, clear)
    - time_of_day: Time of day (morning, day, night)
    - ranger_id: Ranger UUID
    - date_from: Start of date range (inclusive)
    - date_to: End of date range (inclusive)
    - is_confirmed: Confirmation status

    Returns paginated results with total count.
    """
    try:
        sightings_data, total = service.filter_sightings(
            pokemon_id=pokemon_id,
            region=region,
            weather=weather,
            time_of_day=time_of_day,
            ranger_id=ranger_id,
            date_from=date_from,
            date_to=date_to,
            is_confirmed=is_confirmed,
            skip=offset,
            limit=limit,
        )
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e),
            }
        raise HTTPException(status_code=400, detail=str(e)) from None

    results = []
    for sighting, pokemon, ranger in sightings_data:
        results.append(
            SightingResponse(
                id=sighting.id,
                pokemon_id=sighting.pokemon_id,
                ranger_id=sighting.ranger_id,
                region=sighting.region,
                route=sighting.route,
                date=sighting.date,
                weather=sighting.weather,
                time_of_day=sighting.time_of_day,
                height=sighting.height,
                weight=sighting.weight,
                is_shiny=sighting.is_shiny,
                notes=sighting.notes,
                is_confirmed=sighting.is_confirmed,
                campaign_id=sighting.campaign_id,
                pokemon_name=pokemon.name if pokemon else None,
                ranger_name=ranger.name if ranger else None,
            )
        )

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["filter_params"] = {
            "pokemon_id": pokemon_id,
            "region": region,
            "weather": weather,
            "time_of_day": time_of_day,
            "ranger_id": ranger_id,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "is_confirmed": is_confirmed,
        }
        request.state.wide_event["results_count"] = len(results)
        request.state.wide_event["total"] = total

    return PaginatedSightingResponse(
        results=results,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=SightingResponse, status_code=200)
def create_sighting(
    request: Request,
    sighting: SightingCreate,
    service: SightingService = Depends(get_sighting_service),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    if not x_user_id:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "AuthenticationError",
                "message": "Missing X-User-ID header",
            }
        raise HTTPException(
            status_code=401,
            detail="X-User-ID header is required. Please provide your user ID to create a sighting.",
        )

    try:
        new_sighting, pokemon, ranger = service.create_sighting(sighting, x_user_id)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["sighting"] = {
                "id": new_sighting.id,
                "pokemon_id": new_sighting.pokemon_id,
                "pokemon_name": pokemon.name,
                "ranger_id": new_sighting.ranger_id,
                "ranger_name": ranger.name,
                "region": new_sighting.region,
            }

        return SightingResponse(
            id=new_sighting.id,
            pokemon_id=new_sighting.pokemon_id,
            ranger_id=new_sighting.ranger_id,
            region=new_sighting.region,
            route=new_sighting.route,
            date=new_sighting.date,
            weather=new_sighting.weather,
            time_of_day=new_sighting.time_of_day,
            height=new_sighting.height,
            weight=new_sighting.weight,
            is_shiny=new_sighting.is_shiny,
            notes=new_sighting.notes,
            is_confirmed=new_sighting.is_confirmed,
            campaign_id=new_sighting.campaign_id,
            pokemon_name=pokemon.name,
            ranger_name=ranger.name,
        )
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            error_type = "ValidationError"
            if "Ranger" in str(e):
                error_type = "AuthorizationError"
            elif "campaign" in str(e).lower():
                error_type = "CampaignError"
            request.state.wide_event["error"] = {
                "type": error_type,
                "message": str(e),
            }
        if "Ranger" in str(e):
            raise HTTPException(status_code=403, detail=str(e)) from None
        if "campaign" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e)) from None
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get("/{sighting_id}", response_model=SightingResponse)
def get_sighting(
    request: Request,
    sighting_id: str,
    service: SightingService = Depends(get_sighting_service),
):
    result = service.get_sighting(sighting_id)

    if not result:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Sighting with ID '{sighting_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Sighting with ID '{sighting_id}' not found")

    sighting, pokemon, ranger = result

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["sighting"] = {
            "id": sighting.id,
            "pokemon_id": sighting.pokemon_id,
            "region": sighting.region,
        }

    return SightingResponse(
        id=sighting.id,
        pokemon_id=sighting.pokemon_id,
        ranger_id=sighting.ranger_id,
        region=sighting.region,
        route=sighting.route,
        date=sighting.date,
        weather=sighting.weather,
        time_of_day=sighting.time_of_day,
        height=sighting.height,
        weight=sighting.weight,
        is_shiny=sighting.is_shiny,
        notes=sighting.notes,
        is_confirmed=sighting.is_confirmed,
        campaign_id=sighting.campaign_id,
        pokemon_name=pokemon.name if pokemon else None,
        ranger_name=ranger.name if ranger else None,
    )


@router.delete("/{sighting_id}", response_model=MessageResponse)
def delete_sighting(
    request: Request,
    sighting_id: str,
    service: SightingService = Depends(get_sighting_service),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
):
    if not x_user_id:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "AuthenticationError",
                "message": "Missing X-User-ID header",
            }
        raise HTTPException(
            status_code=401,
            detail="X-User-ID header is required. Please provide your user ID to delete a sighting.",
        )

    try:
        success = service.delete_sighting(sighting_id, x_user_id)
        if success:
            if hasattr(request.state, "wide_event"):
                request.state.wide_event["sighting"] = {
                    "id": sighting_id,
                    "deleted": True,
                }
            return MessageResponse(detail="Sighting deleted successfully")
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            error_type = "AuthorizationError" if "Permission denied" in str(e) else "NotFoundError"
            if "campaign" in str(e).lower() or "locked" in str(e).lower():
                error_type = "CampaignLockError"
            request.state.wide_event["error"] = {
                "type": error_type,
                "message": str(e),
            }
        if "Permission denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e)) from None
        if "campaign" in str(e).lower() or "locked" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e)) from None
        raise HTTPException(status_code=404, detail=str(e)) from None
