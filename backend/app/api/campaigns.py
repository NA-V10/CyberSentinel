"""FastAPI router: Attack Campaign Detection endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.audit_log_service import log_event
from backend.app.services.campaign_detection_service import (
    detect_campaigns,
    get_campaign_by_id,
    get_campaigns,
)

router = APIRouter()


class IncidentInput(BaseModel):
    id: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    attack_type: Optional[str] = None
    severity: Optional[str] = None
    protocol: Optional[str] = None
    mitre_technique: Optional[str] = None
    timestamp: Optional[str] = None


class CampaignDetectRequest(BaseModel):
    incidents: List[IncidentInput] = Field(..., min_length=2)
    time_window_hours: int = Field(default=24, ge=1, le=168)


class CampaignResponse(BaseModel):
    campaigns: List[Dict[str, Any]]
    total_detected: int
    incidents_analyzed: int
    time_window_hours: int


@router.post(
    "/detect",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect attack campaigns from a group of incidents",
)
async def detect_campaigns_endpoint(
    request: CampaignDetectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> CampaignResponse:
    """
    Detect coordinated attack campaigns from a list of incidents.

    Uses IP subnet correlation, MITRE technique matching, attack pattern
    similarity, and temporal clustering to group related incidents.

    **Example Request:**
    ```json
    {
      "incidents": [
        {"id": "INC-102", "source_ip": "45.33.32.156", "attack_type": "Brute Force", "severity": "high"},
        {"id": "INC-118", "source_ip": "45.33.32.188", "attack_type": "Brute Force", "severity": "high"},
        {"id": "INC-130", "source_ip": "45.33.32.201", "attack_type": "SSH Brute Force", "severity": "medium"}
      ],
      "time_window_hours": 24
    }
    ```

    **Example Response:**
    ```json
    {
      "campaigns": [{
        "campaign_name": "Credential Harvesting Campaign",
        "campaign_confidence": 91,
        "related_incidents": ["INC-102", "INC-118", "INC-130"],
        "shared_indicators": ["source subnet 45.33.x.x", "MITRE T1110"],
        "recommended_campaign_response": "Block subnet, rotate credentials"
      }],
      "total_detected": 1
    }
    ```
    """
    user_id = current_user.get("user_id", "unknown")
    org_id = current_user.get("org_id", "default")

    incidents_data = [inc.model_dump(exclude_none=True) for inc in request.incidents]

    result = await detect_campaigns(
        incidents=incidents_data,
        org_id=org_id,
        user_id=user_id,
        db=db,
        time_window_hours=request.time_window_hours,
    )

    await log_event(
        db=db,
        org_id=org_id,
        user_id=user_id,
        event_type="campaign_detected",
        resource_type="campaigns",
        details={
            "incidents_analyzed": len(request.incidents),
            "campaigns_found": result.get("total_detected", 0),
        },
    )

    return CampaignResponse(**result)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List all detected campaigns for the organisation",
)
async def list_campaigns(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve all campaigns detected for the current organisation."""
    org_id = current_user.get("org_id", "default")
    campaigns = await get_campaigns(db=db, org_id=org_id, limit=limit)
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.get(
    "/{campaign_id}",
    status_code=status.HTTP_200_OK,
    summary="Get campaign details by ID",
)
async def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve detailed information about a specific campaign."""
    org_id = current_user.get("org_id", "default")
    campaign = await get_campaign_by_id(db=db, campaign_id=campaign_id, org_id=org_id)
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
