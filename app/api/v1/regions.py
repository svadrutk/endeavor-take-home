from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_region_service
from app.schemas import RegionalSummary
from app.services.region_service import RegionService

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/{region_name}/summary", response_model=RegionalSummary)
def get_regional_summary(
    request: Request,
    region_name: str,
    service: RegionService = Depends(get_region_service),
):
    """
    Get comprehensive research summary for a region.

    Returns:
    - Total sightings with confirmation breakdown
    - Unique species count
    - Top 5 most-sighted Pokemon
    - Top 5 contributing Rangers
    - Weather condition breakdown
    - Time of day breakdown
    """
    try:
        summary = service.get_regional_summary(region_name)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["region"] = region_name
            request.state.wide_event["summary"] = {
                "total_sightings": summary["total_sightings"],
                "unique_species": summary["unique_species"],
            }

        return RegionalSummary(**summary)

    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e),
            }
        raise HTTPException(status_code=404, detail=str(e)) from None
