from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.logging_config import configure_logging
from app.middleware import WideEventMiddleware
from app.schemas import (
    MessageResponse,
    PaginatedPokemonResponse,
    PaginatedPokemonSearchResult,
    PaginatedSightingResponse,
    PokemonResponse,
    PokemonSearchResult,
    RangerCreate,
    RangerResponse,
    SightingCreate,
    SightingResponse,
    TrainerCreate,
    TrainerResponse,
    UserLookupResponse,
)
from app.services import PokemonService, RangerService, SightingService, TrainerService

configure_logging(log_level="INFO")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Endeavor PokéTracker", version="0.0.1")

app.add_middleware(WideEventMiddleware)  # ty: ignore[invalid-argument-type]

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)  # ty: ignore[invalid-argument-type]


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "RateLimitExceeded",
            "message": "Rate limit exceeded",
        }
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "ValueError",
            "message": str(exc),
        }
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    return {"message": "Welcome to PokéTracker API"}


@app.post("/trainers", response_model=TrainerResponse, status_code=200)
@limiter.limit("10/minute")
def create_trainer(
    request: Request,
    trainer: TrainerCreate,
    db: Session = Depends(get_db),
):
    service = TrainerService(db)
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


@app.get("/trainers/{trainer_id}", response_model=TrainerResponse)
@limiter.limit("100/minute")
def get_trainer(
    request: Request,
    trainer_id: str,
    db: Session = Depends(get_db),
):
    service = TrainerService(db)
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


@app.post("/rangers", response_model=RangerResponse, status_code=200)
@limiter.limit("10/minute")
def create_ranger(
    request: Request,
    ranger: RangerCreate,
    db: Session = Depends(get_db),
):
    service = RangerService(db)
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


@app.get("/rangers/{ranger_id}", response_model=RangerResponse)
@limiter.limit("100/minute")
def get_ranger(
    request: Request,
    ranger_id: str,
    db: Session = Depends(get_db),
):
    service = RangerService(db)
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


@app.get("/rangers/{ranger_id}/sightings", response_model=PaginatedSightingResponse)
@limiter.limit("100/minute")
def get_ranger_sightings(
    request: Request,
    ranger_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = SightingService(db)
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


@app.get("/users/lookup", response_model=UserLookupResponse)
@limiter.limit("100/minute")
def lookup_user(
    request: Request,
    name: str = Query(...),
    db: Session = Depends(get_db),
):
    trainer_service = TrainerService(db)
    result = trainer_service.lookup_user_by_name(name)
    if result:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["user"] = {
                "id": result["id"],
                "role": result["role"],
            }
        return result

    ranger_service = RangerService(db)
    result = ranger_service.lookup_user_by_name(name)
    if result:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["user"] = {
                "id": result["id"],
                "role": result["role"],
            }
        return result

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "NotFoundError",
            "message": f"User with name '{name}' not found",
        }
    raise HTTPException(status_code=404, detail=f"User with name '{name}' not found")


@app.get("/pokedex", response_model=PaginatedPokemonResponse)
@limiter.limit("100/minute")
def list_pokemon(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = PokemonService(db)
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


@app.get("/pokedex/search", response_model=PaginatedPokemonSearchResult)
@limiter.limit("100/minute")
def search_pokemon(
    request: Request,
    name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = PokemonService(db)
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


@app.get("/pokedex/{pokemon_id}", response_model=PokemonResponse)
@limiter.limit("100/minute")
def get_pokemon(
    request: Request,
    pokemon_id: int,
    db: Session = Depends(get_db),
):
    service = PokemonService(db)
    pokemon = service.get_pokemon(pokemon_id)
    if not pokemon:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Pokemon with ID '{pokemon_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Pokemon with ID '{pokemon_id}' not found")
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["pokemon"] = {"id": pokemon.id, "name": pokemon.name}
    return PokemonResponse.model_validate(pokemon)


@app.get("/pokedex/region/{region_name_or_generation}")
@limiter.limit("100/minute")
def get_pokemon_by_region(
    request: Request,
    region_name_or_generation: str,
    db: Session = Depends(get_db),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int | None = Query(None, ge=0),
):
    service = PokemonService(db)
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


@app.post("/sightings", response_model=SightingResponse, status_code=200)
@limiter.limit("10/minute")
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


@app.get("/sightings/{sighting_id}", response_model=SightingResponse)
@limiter.limit("100/minute")
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


@app.delete("/sightings/{sighting_id}", response_model=MessageResponse)
@limiter.limit("10/minute")
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
