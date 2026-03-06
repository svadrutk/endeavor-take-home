from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.deps import get_campaign_service
from app.models import CampaignStatus
from app.schemas import (
    CampaignCreate,
    CampaignResponse,
    CampaignSummary,
    CampaignUpdate,
)
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=201)
def create_campaign(
    request: Request,
    campaign: CampaignCreate,
    service: CampaignService = Depends(get_campaign_service),
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
            detail="X-User-ID header is required. Please provide your user ID to create a campaign.",
        )

    try:
        new_campaign, ranger = service.create_campaign(campaign, x_user_id)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["campaign"] = {
                "id": new_campaign.id,
                "name": new_campaign.name,
                "region": new_campaign.region,
                "status": new_campaign.status,
                "created_by": ranger.name,
            }

        return CampaignResponse.model_validate(new_campaign)
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            error_type = "ValidationError"
            if "Ranger" in str(e):
                error_type = "AuthorizationError"
            request.state.wide_event["error"] = {
                "type": error_type,
                "message": str(e),
            }
        if "Ranger" in str(e):
            raise HTTPException(status_code=403, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    request: Request,
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
):
    campaign = service.get_campaign(campaign_id)

    if not campaign:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": f"Campaign with ID '{campaign_id}' not found",
            }
        raise HTTPException(status_code=404, detail=f"Campaign with ID '{campaign_id}' not found")

    if hasattr(request.state, "wide_event"):
        request.state.wide_event["campaign"] = {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
        }

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    request: Request,
    campaign_id: str,
    campaign_update: CampaignUpdate,
    service: CampaignService = Depends(get_campaign_service),
):
    try:
        updated_campaign = service.update_campaign(campaign_id, campaign_update)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["campaign"] = {
                "id": updated_campaign.id,
                "name": updated_campaign.name,
                "status": updated_campaign.status,
            }

        return CampaignResponse.model_validate(updated_campaign)
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            error_type = "ValidationError"
            if "not found" in str(e).lower():
                error_type = "NotFoundError"
            elif "Cannot update" in str(e):
                error_type = "StateTransitionError"
            request.state.wide_event["error"] = {
                "type": error_type,
                "message": str(e),
            }
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/{campaign_id}/transition", response_model=CampaignResponse)
def transition_campaign(
    request: Request,
    campaign_id: str,
    new_status: CampaignStatus,
    service: CampaignService = Depends(get_campaign_service),
):
    try:
        updated_campaign = service.transition_campaign(campaign_id, new_status)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["campaign"] = {
                "id": updated_campaign.id,
                "name": updated_campaign.name,
                "old_status": campaign_id,
                "new_status": updated_campaign.status,
            }

        return CampaignResponse.model_validate(updated_campaign)
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            error_type = "StateTransitionError"
            if "not found" in str(e).lower():
                error_type = "NotFoundError"
            request.state.wide_event["error"] = {
                "type": error_type,
                "message": str(e),
            }
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/{campaign_id}/summary", response_model=CampaignSummary)
def get_campaign_summary(
    request: Request,
    campaign_id: str,
    service: CampaignService = Depends(get_campaign_service),
):
    try:
        summary = service.get_campaign_summary(campaign_id)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["campaign_summary"] = {
                "campaign_id": summary["campaign_id"],
                "total_sightings": summary["total_sightings"],
                "unique_species": summary["unique_species"],
            }

        return CampaignSummary(**summary)
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "NotFoundError",
                "message": str(e),
            }
        raise HTTPException(status_code=404, detail=str(e)) from None
