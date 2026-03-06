from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import MessageResponse, SightingCreate, SightingResponse
from app.services import SightingService

router = APIRouter(prefix="/sightings", tags=["sightings"])


@router.post("/", response_model=SightingResponse, status_code=200)
def create_sighting(
    request: Request,
    sighting: SightingCreate,
    db: Session = Depends(get_db),
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

    service = SightingService(db)
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
            pokemon_name=pokemon.name,
            ranger_name=ranger.name,
        )
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError" if "Ranger" not in str(e) else "AuthorizationError",
                "message": str(e),
            }
        if "Ranger" in str(e):
            raise HTTPException(status_code=403, detail=str(e)) from None
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get("/{sighting_id}", response_model=SightingResponse)
def get_sighting(
    request: Request,
    sighting_id: str,
    db: Session = Depends(get_db),
):
    service = SightingService(db)
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
        pokemon_name=pokemon.name if pokemon else None,
        ranger_name=ranger.name if ranger else None,
    )


@router.delete("/{sighting_id}", response_model=MessageResponse)
def delete_sighting(
    request: Request,
    sighting_id: str,
    db: Session = Depends(get_db),
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

    service = SightingService(db)
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
            request.state.wide_event["error"] = {
                "type": "AuthorizationError" if "Permission denied" in str(e) else "NotFoundError",
                "message": str(e),
            }
        if "Permission denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e)) from None
        raise HTTPException(status_code=404, detail=str(e)) from None
