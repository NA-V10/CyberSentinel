"""FastAPI router: Simulation mode endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.clerk import get_current_user
from backend.app.services.simulation_service import get_scenarios, run_scenario

router = APIRouter()


@router.get(
    "/scenarios",
    status_code=status.HTTP_200_OK,
    summary="List available simulation scenarios",
)
async def list_scenarios(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return all available pre-built attack simulation scenarios."""
    return get_scenarios()


@router.post(
    "/run/{scenario_id}",
    status_code=status.HTTP_200_OK,
    summary="Get scenario incident data ready for analysis",
)
async def run_simulation_scenario(
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the full incident payload for a scenario, ready to submit to the analysis pipeline."""
    result = await run_scenario(scenario_id=scenario_id, user_id=current_user["user_id"])
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
