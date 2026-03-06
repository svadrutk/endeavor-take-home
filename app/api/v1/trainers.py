from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import TrainerCreate, TrainerResponse
from app.services import TrainerService

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.post("/", response_model=TrainerResponse, status_code=200)
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


@router.get("/{trainer_id}", response_model=TrainerResponse)
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
