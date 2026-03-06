from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_ranger_service, get_sighting_service
from app.schemas import (
    PaginatedSightingResponse,
    RangerCreate,
    RangerResponse,
    SightingResponse,
)
from app.services import RangerService, SightingService

router = APIRouter(prefix="/rangers", tags=["rangers"])


@router.post("/", response_model=RangerResponse, status_code=200)
def create_ranger(
    request: Request,
    ranger: RangerCreate,
    service: RangerService = Depends(get_ranger_service),
):
    try:
        new_ranger = service.create_ranger(ranger)
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["ranger"] = {
                "id": new_ranger.id,
                "name": new_ranger.name,
            }
        return new_ranger
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ConflictError",
                "message": str(e),
            }
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/{ranger_id}", response_model=RangerResponse)
def get_ranger(
    request: Request,
    ranger_id: str,
    service: RangerService = Depends(get_ranger_service),
):
    ranger = service.get_ranger(ranger_id)
    if not ranger:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Ranger with ID '{ranger_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Ranger with ID '{ranger_id}' not found")
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["ranger"] = {"id": ranger.id, "name": ranger.name}
    return ranger


@router.get("/{ranger_id}/sightings", response_model=PaginatedSightingResponse)
def get_ranger_sightings(
    request: Request,
    ranger_id: str,
    service: SightingService = Depends(get_sighting_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        sightings_data, total = service.get_ranger_sightings(ranger_id, skip=offset, limit=limit)

        result = []
        for sighting, pokemon, ranger in sightings_data:
            result.append(
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
                    pokemon_name=pokemon.name if pokemon else None,
                    ranger_name=ranger.name if ranger else None,
                )
            )

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["ranger_id"] = ranger_id
            request.state.wide_event["sightings_count"] = len(result)
            request.state.wide_event["total_sightings"] = total

        return PaginatedSightingResponse(
            results=result,
            total=total,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": str(e),
            }
        raise HTTPException(status_code=404, detail=str(e)) from None
