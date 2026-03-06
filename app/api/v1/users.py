from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_ranger_service, get_trainer_service
from app.schemas import UserLookupResponse
from app.services import RangerService, TrainerService

router = APIRouter(tags=["users"])


@router.get("/users/lookup", response_model=UserLookupResponse)
def lookup_user(
    request: Request,
    name: str = Query(...),
    trainer_service: TrainerService = Depends(get_trainer_service),
    ranger_service: RangerService = Depends(get_ranger_service),
):
    result = trainer_service.lookup_user_by_name(name)
    if result:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["user"] = {
                "id": result["id"],
                "role": result["role"],
            }
        return result

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
