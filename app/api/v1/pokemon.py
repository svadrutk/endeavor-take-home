from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.api.deps import get_pokemon_service, get_trainer_service
from app.schemas import (
    PaginatedPokemonResponse,
    PaginatedPokemonSearchResult,
    PokemonResponse,
    PokemonSearchResult,
)
from app.services import PokemonService, TrainerService

router = APIRouter(prefix="/pokedex", tags=["pokemon"])


@router.get("/", response_model=PaginatedPokemonResponse)
def list_pokemon(
    request: Request,
    service: PokemonService = Depends(get_pokemon_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    pokemon_list, total = service.list_pokemon(skip=offset, limit=limit)

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["pokemon_count"] = len(pokemon_list)
        request.state.wide_event["total_pokemon"] = total

    return PaginatedPokemonResponse(
        results=[PokemonResponse.model_validate(p) for p in pokemon_list],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=PaginatedPokemonSearchResult)
def search_pokemon(
    request: Request,
    name: str = Query(..., min_length=1),
    service: PokemonService = Depends(get_pokemon_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    pokemon_list, total = service.search_pokemon(name, skip=offset, limit=limit)

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["search_term"] = name
        request.state.wide_event["results_count"] = len(pokemon_list)

    return PaginatedPokemonSearchResult(
        results=[PokemonSearchResult.model_validate(p) for p in pokemon_list],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{pokemon_id}", response_model=PokemonResponse)
def get_pokemon(
    request: Request,
    pokemon_id: int,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    pokemon_service: PokemonService = Depends(get_pokemon_service),
    trainer_service: TrainerService = Depends(get_trainer_service),
):
    pokemon = pokemon_service.get_pokemon(pokemon_id)
    if not pokemon:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Pokemon with ID '{pokemon_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Pokemon with ID '{pokemon_id}' not found")

    response_data = PokemonResponse.model_validate(pokemon)

    if x_user_id:
        trainer = trainer_service.get_trainer(x_user_id)
        if trainer:
            is_caught = trainer_service.has_caught_pokemon(x_user_id, pokemon_id)
            response_data.is_caught = is_caught

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["pokemon"] = {"id": pokemon.id, "name": pokemon.name}
    return response_data


@router.get("/region/{region_name_or_generation}")
def get_pokemon_by_region(
    request: Request,
    region_name_or_generation: str,
    service: PokemonService = Depends(get_pokemon_service),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int | None = Query(None, ge=0),
):
    try:
        pokemon_list, total = service.get_pokemon_by_region(region_name_or_generation)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["region"] = region_name_or_generation
            request.state.wide_event["pokemon_count"] = len(pokemon_list)

        if limit is not None and offset is not None:
            paginated_list = pokemon_list[offset : offset + limit]
            return PaginatedPokemonResponse(
                results=[PokemonResponse.model_validate(p) for p in paginated_list],
                total=total,
                limit=limit,
                offset=offset,
            )
        else:
            return [PokemonResponse.model_validate(p) for p in pokemon_list]
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e),
            }
        raise HTTPException(status_code=400, detail=str(e)) from None
