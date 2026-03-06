from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_current_user, get_trainer_service
from app.schemas import (
    CatchLogResponse,
    CatchSummaryResponse,
    MessageResponse,
    TrainerCatchResponse,
    TrainerCreate,
    TrainerResponse,
)
from app.services import TrainerService

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.post("/", response_model=TrainerResponse, status_code=200)
def create_trainer(
    request: Request,
    trainer: TrainerCreate,
    service: TrainerService = Depends(get_trainer_service),
):
    try:
        new_trainer = service.create_trainer(trainer)
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["trainer"] = {
                "id": new_trainer.id,
                "name": new_trainer.name,
            }
        return new_trainer
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ConflictError",
                "message": str(e),
            }
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/{trainer_id}", response_model=TrainerResponse)
def get_trainer(
    request: Request,
    trainer_id: str,
    service: TrainerService = Depends(get_trainer_service),
):
    trainer = service.get_trainer(trainer_id)
    if not trainer:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Trainer with ID '{trainer_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Trainer with ID '{trainer_id}' not found")
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["trainer"] = {"id": trainer.id, "name": trainer.name}
    return trainer


@router.post("/{trainer_id}/pokedex/{pokemon_id}", response_model=TrainerCatchResponse)
def mark_pokemon_caught(
    request: Request,
    trainer_id: str,
    pokemon_id: int,
    current_user: dict = Depends(get_current_user),
    service: TrainerService = Depends(get_trainer_service),
):
    if current_user["role"] != "trainer":
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "AuthorizationError",
                "message": "Only Pokémon Trainers can use catch-tracking features. Rangers do not have access to this functionality.",
            }
        raise HTTPException(
            status_code=403,
            detail="Only Pokémon Trainers can use catch-tracking features. Rangers do not have access to this functionality.",
        )

    try:
        catch, pokemon = service.mark_pokemon_caught(trainer_id, pokemon_id, current_user["id"])
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["catch"] = {
                "trainer_id": trainer_id,
                "pokemon_id": pokemon_id,
                "pokemon_name": pokemon.name,
            }
        return TrainerCatchResponse(
            pokemon_id=pokemon_id,
            pokemon_name=pokemon.name,
            caught_at=catch.caught_at,
        )
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ConflictError" if "already" in str(e).lower() else "NotFoundError",
                "message": str(e),
            }
        status_code = (
            409 if "already" in str(e).lower() else 404 if "not found" in str(e).lower() else 403
        )
        raise HTTPException(status_code=status_code, detail=str(e)) from None


@router.delete("/{trainer_id}/pokedex/{pokemon_id}", response_model=MessageResponse)
def unmark_pokemon_caught(
    request: Request,
    trainer_id: str,
    pokemon_id: int,
    current_user: dict = Depends(get_current_user),
    service: TrainerService = Depends(get_trainer_service),
):
    if current_user["role"] != "trainer":
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "AuthorizationError",
                "message": "Only Pokémon Trainers can use catch-tracking features. Rangers do not have access to this functionality.",
            }
        raise HTTPException(
            status_code=403,
            detail="Only Pokémon Trainers can use catch-tracking features. Rangers do not have access to this functionality.",
        )

    try:
        service.unmark_pokemon_caught(trainer_id, pokemon_id, current_user["id"])
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["unmark"] = {
                "trainer_id": trainer_id,
                "pokemon_id": pokemon_id,
            }
        return MessageResponse(detail="Pokemon removed from catch log")
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError" if "not in" in str(e).lower() else "AuthorizationError",
                "message": str(e),
            }
        status_code = 404 if "not in" in str(e).lower() or "not found" in str(e).lower() else 403
        raise HTTPException(status_code=status_code, detail=str(e)) from None


@router.get("/{trainer_id}/pokedex", response_model=CatchLogResponse)
def get_catch_log(
    request: Request,
    trainer_id: str,
    service: TrainerService = Depends(get_trainer_service),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    trainer = service.get_trainer(trainer_id)
    if not trainer:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Trainer with ID '{trainer_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Trainer with ID '{trainer_id}' not found")

    catches = service.get_catch_log(trainer_id, skip=offset, limit=limit)
    total = (
        service.trainer_catch_repo.count_by_trainer(trainer_id) if service.trainer_catch_repo else 0
    )

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["catch_log"] = {
            "trainer_id": trainer_id,
            "total_catches": total,
        }

    return CatchLogResponse(
        trainer_id=trainer_id,
        trainer_name=trainer.name,
        catches=[
            TrainerCatchResponse(
                pokemon_id=catch.pokemon_id,
                pokemon_name=catch.pokemon.name,
                caught_at=catch.caught_at,
            )
            for catch in catches
        ],
        total=total,
    )


@router.get("/{trainer_id}/pokedex/summary", response_model=CatchSummaryResponse)
def get_catch_summary(
    request: Request,
    trainer_id: str,
    service: TrainerService = Depends(get_trainer_service),
):
    trainer = service.get_trainer(trainer_id)
    if not trainer:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Trainer with ID '{trainer_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Trainer with ID '{trainer_id}' not found")

    summary = service.get_catch_summary(trainer_id)

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["catch_summary"] = {
            "trainer_id": trainer_id,
            "total_caught": summary["total_caught"],
            "completion_percentage": summary["completion_percentage"],
        }

    return CatchSummaryResponse(
        trainer_id=trainer_id,
        trainer_name=trainer.name,
        total_caught=summary["total_caught"],
        completion_percentage=summary["completion_percentage"],
        caught_by_type=summary["caught_by_type"],
        caught_by_generation=summary["caught_by_generation"],
    )
