from fastapi import FastAPI, HTTPException, Header, Query, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import Optional, Any
from datetime import datetime

from app.database import engine, SessionLocal, Base
from app.models import Pokemon, Trainer, Ranger, Sighting
from app.schemas import (
    TrainerCreate,
    TrainerResponse,
    RangerCreate,
    RangerResponse,
    PokemonResponse,
    PokemonSearchResult,
    SightingCreate,
    SightingResponse,
    UserLookupResponse,
    MessageResponse,
    PaginatedSightingResponse,
    PaginatedPokemonResponse,
    PaginatedPokemonSearchResult,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Endeavor PokéTracker", version="0.0.1")


# ---------- helpers ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


REGION_TO_GENERATION = {
    "kanto": 1,
    "johto": 2,
    "hoenn": 3,
    "sinnoh": 4,
}


# ---------- Trainers ----------

@app.post("/trainers", response_model=TrainerResponse)
def create_trainer(trainer: TrainerCreate, db: Session = Depends(get_db)):
    new_trainer = Trainer(name=trainer.name, email=trainer.email)
    db.add(new_trainer)
    try:
        db.commit()
        db.refresh(new_trainer)
        return new_trainer
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Trainer with this name or email already exists")


@app.get("/trainers/{trainer_id}", response_model=TrainerResponse)
def get_trainer(trainer_id: str, db: Session = Depends(get_db)):
    trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer


# ---------- Rangers ----------

@app.post("/rangers", response_model=RangerResponse)
def create_ranger(ranger: RangerCreate, db: Session = Depends(get_db)):
    new_ranger = Ranger(
        name=ranger.name,
        email=ranger.email,
        specialization=ranger.specialization,
    )
    db.add(new_ranger)
    try:
        db.commit()
        db.refresh(new_ranger)
        return new_ranger
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ranger with this name or email already exists")


@app.get("/rangers/{ranger_id}", response_model=RangerResponse)
def get_ranger(ranger_id: str, db: Session = Depends(get_db)):
    ranger = db.query(Ranger).filter(Ranger.id == ranger_id).first()
    if not ranger:
        raise HTTPException(status_code=404, detail="Ranger not found")
    return ranger


@app.get("/rangers/{ranger_id}/sightings", response_model=PaginatedSightingResponse)
def get_ranger_sightings(
    ranger_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ranger = db.query(Ranger).filter(Ranger.id == ranger_id).first()
    if not ranger:
        raise HTTPException(status_code=404, detail="Ranger not found")
    
    total = db.query(Sighting).filter(Sighting.ranger_id == ranger_id).count()
    
    sightings = (
        db.query(Sighting)
        .options(joinedload(Sighting.pokemon))
        .filter(Sighting.ranger_id == ranger_id)
        .order_by(Sighting.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    result = []
    for s in sightings:
        resp = SightingResponse.model_validate(s)
        resp.pokemon_name = s.pokemon.name if s.pokemon else None
        resp.ranger_name = ranger.name
        result.append(resp)
    
    return PaginatedSightingResponse(
        results=result,
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------- User Lookup ----------

@app.get("/users/lookup", response_model=UserLookupResponse)
def lookup_user(name: str = Query(...), db: Session = Depends(get_db)):
    trainer = db.query(Trainer).filter(Trainer.name == name).first()
    if trainer:
        return UserLookupResponse(id=trainer.id, name=trainer.name, role="trainer")
    ranger = db.query(Ranger).filter(Ranger.name == name).first()
    if ranger:
        return UserLookupResponse(id=ranger.id, name=ranger.name, role="ranger")
    raise HTTPException(status_code=404, detail="User not found")


# ---------- Pokédex ----------

@app.get("/pokedex", response_model=PaginatedPokemonResponse)
def list_pokemon(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    total = db.query(Pokemon).count()
    pokemon_list = db.query(Pokemon).order_by(Pokemon.id).limit(limit).offset(offset).all()
    return PaginatedPokemonResponse(
        results=[PokemonResponse.model_validate(p) for p in pokemon_list],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/pokedex/search", response_model=PaginatedPokemonSearchResult)
def search_pokemon(
    name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    total = db.query(Pokemon).filter(Pokemon.name.ilike(f"%{name}%")).count()
    results = (
        db.query(Pokemon)
        .filter(Pokemon.name.ilike(f"%{name}%"))
        .order_by(Pokemon.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return PaginatedPokemonSearchResult(
        results=[PokemonSearchResult.model_validate(p) for p in results],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/pokedex/{pokemon_id}", response_model=PokemonResponse)
def get_pokemon(pokemon_id: int, db: Session = Depends(get_db)):
    pokemon = db.query(Pokemon).filter(Pokemon.id == pokemon_id).first()
    if not pokemon:
        raise HTTPException(status_code=404, detail="Pokémon not found")
    return PokemonResponse.model_validate(pokemon)


@app.get("/pokedex/region/{region_name_or_generation}", response_model=list[PokemonResponse])
def get_pokemon_by_region(region_name_or_generation: str, db: Session = Depends(get_db)):
    region_lower = region_name_or_generation.lower()
    generation = REGION_TO_GENERATION.get(region_lower)
    if generation is None:
        try:
            generation = int(region_name_or_generation)
        except ValueError:
            raise HTTPException(status_code=404, detail="Invalid region name or generation number")
    
    if generation < 1 or generation > 4:
        raise HTTPException(status_code=404, detail="Generation must be between 1 and 4")
    
    pokemon_list = db.query(Pokemon).filter(Pokemon.generation == generation).all()
    return [PokemonResponse.model_validate(p) for p in pokemon_list]


# ---------- Sightings ----------

@app.post("/sightings", response_model=SightingResponse)
def create_sighting(
    sighting: SightingCreate,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header is required")

    # Check that user is a ranger
    ranger = db.query(Ranger).filter(Ranger.id == x_user_id).first()
    if not ranger:
        raise HTTPException(status_code=403, detail="Only rangers can log sightings")

    # Check pokemon exists
    pokemon = db.query(Pokemon).filter(Pokemon.id == sighting.pokemon_id).first()
    if not pokemon:
        raise HTTPException(status_code=404, detail="Pokémon not found")

    new_sighting = Sighting(
        pokemon_id=sighting.pokemon_id,
        ranger_id=x_user_id,
        region=sighting.region,
        route=sighting.route,
        date=sighting.date,
        weather=sighting.weather,
        time_of_day=sighting.time_of_day,
        height=sighting.height,
        weight=sighting.weight,
        is_shiny=sighting.is_shiny,
        notes=sighting.notes,
        latitude=sighting.latitude,
        longitude=sighting.longitude,
    )
    db.add(new_sighting)
    db.commit()
    db.refresh(new_sighting)

    resp = SightingResponse.model_validate(new_sighting)
    resp.pokemon_name = pokemon.name
    resp.ranger_name = ranger.name
    return resp


@app.get("/sightings/{sighting_id}", response_model=SightingResponse)
def get_sighting(sighting_id: str, db: Session = Depends(get_db)):
    sighting = db.query(Sighting).filter(Sighting.id == sighting_id).first()
    if not sighting:
        raise HTTPException(status_code=404, detail="Sighting not found")

    pokemon = db.query(Pokemon).filter(Pokemon.id == sighting.pokemon_id).first()
    ranger = db.query(Ranger).filter(Ranger.id == sighting.ranger_id).first()

    resp = SightingResponse.model_validate(sighting)
    resp.pokemon_name = pokemon.name if pokemon else None
    resp.ranger_name = ranger.name if ranger else None
    return resp


@app.delete("/sightings/{sighting_id}", response_model=MessageResponse)
def delete_sighting(
    sighting_id: str,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header is required")

    sighting = db.query(Sighting).filter(Sighting.id == sighting_id).first()
    if not sighting:
        raise HTTPException(status_code=404, detail="Sighting not found")

    if sighting.ranger_id != x_user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own sightings")

    db.delete(sighting)
    db.commit()
    return MessageResponse(detail="Sighting deleted")
