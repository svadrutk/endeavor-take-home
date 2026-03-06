from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_current_user, get_region_service
from app.schemas import RegionalAnalysis, RegionalSummary
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


@router.get("/{region_name}/analysis", response_model=RegionalAnalysis)
def get_regional_analysis(
    request: Request,
    region_name: str,
    current_user: dict = Depends(get_current_user),
    service: RegionService = Depends(get_region_service),
):
    """
    Get rarity tier analysis for a region with anomaly detection.

    Returns:
    - Total sightings count
    - Rarity tier breakdown (mythical, legendary, rare, uncommon, common)
    - Species counts within each tier
    - Anomalies: species with notably high or low sighting frequencies

    Authentication required.
    """
    try:
        analysis = service.get_regional_analysis(region_name)

        if hasattr(request.state, "wide_event"):
            request.state.wide_event["region"] = region_name
            request.state.wide_event["user_id"] = current_user["id"]
            request.state.wide_event["analysis"] = {
                "total_sightings": analysis["total_sightings"],
                "anomaly_count": len(analysis["anomalies"]),
            }

        return RegionalAnalysis(**analysis)

    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e),
            }
        raise HTTPException(status_code=404, detail=str(e)) from None
