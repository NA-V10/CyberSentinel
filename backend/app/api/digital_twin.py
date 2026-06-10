"""FastAPI router: AI SOC Digital Twin Simulator endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from backend.app.auth.clerk import get_current_user
from backend.app.core.database import get_db
from backend.app.services.audit_log_service import log_event
from backend.app.services.digital_twin_service import (
    compare_runs,
    get_scenarios,
    run_scenario,
)

router = APIRouter()


class CompareRunsRequest(BaseModel):
    run_ids: List[str] = Field(..., min_length=2, max_length=5)


@router.get(
    "/scenarios",
    status_code=status.HTTP_200_OK,
    summary="List all available simulation scenarios",
)
async def list_scenarios(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return all built-in simulation scenarios for the digital twin.

    Scenarios available:
    - **Phishing Campaign**: Targeted spearphishing with malicious attachments
    - **Malware Outbreak**: Ransomware spreading via SMB
    - **DDoS Spike**: Large-scale distributed denial of service
    - **Insider Threat**: Malicious insider data exfiltration
    - **SSH Brute Force**: Coordinated brute force on exposed SSH
    - **Data Exfiltration**: Covert DNS tunneling exfiltration
    """
    scenarios = get_scenarios()
    return {"scenarios": scenarios, "total": len(scenarios)}


@router.post(
    "/run/{scenario_id}",
    status_code=status.HTTP_200_OK,
    summary="Run a simulation scenario",
)
async def run_simulation(
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute a simulation scenario and return the full results.

    Generates synthetic incidents, runs the agent pipeline on each,
    then compares expected vs actual outcomes with accuracy scoring.

    **Workflow:**
    ```
    Launch Scenario → Generate Synthetic Incidents → Watch Agents Respond
    → Review Decisions → Compare Expected vs Actual
    ```

    **Example Response:**
    ```json
    {
      "run_id": "abc-123",
      "scenario_name": "SSH Brute Force",
      "accuracy_score": 91.7,
      "response_quality_score": 88.3,
      "comparison_summary": "Excellent performance: 91.7% accuracy on 6 synthetic incidents."
    }
    ```
    """
    user_id = current_user.get("user_id", "unknown")
    org_id = current_user.get("org_id", "default")

    result = await run_scenario(
        scenario_id=scenario_id,
        org_id=org_id,
        user_id=user_id,
    )

    await log_event(
        db=db,
        org_id=org_id,
        user_id=user_id,
        event_type="digital_twin_simulation_run",
        resource_type="simulation",
        resource_id=result.get("run_id"),
        details={
            "scenario_id": scenario_id,
            "scenario_name": result.get("scenario_name"),
            "accuracy_score": result.get("accuracy_score"),
            "incident_count": len(result.get("synthetic_incidents", [])),
        },
    )

    return result


@router.get(
    "/runs/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Get simulation run details",
)
async def get_run(
    run_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve details of a specific simulation run by ID."""
    return {
        "run_id": run_id,
        "status": "completed",
        "note": "Run stored in database — implement DB lookup for production use",
    }


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    summary="Compare multiple simulation runs",
)
async def compare_simulation_runs(
    request: CompareRunsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compare accuracy and quality metrics across multiple simulation runs."""
    org_id = current_user.get("org_id", "default")
    return await compare_runs(run_ids=request.run_ids, org_id=org_id)
