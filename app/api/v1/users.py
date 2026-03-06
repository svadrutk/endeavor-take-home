from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import UserLookupResponse
from app.services import RangerService, TrainerService

router = APIRouter(tags=["users"])


@router.get("/users/lookup", response_model=UserLookupResponse)
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
