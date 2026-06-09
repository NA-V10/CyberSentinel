"""FastAPI router: Threat intelligence enrichment endpoint."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from backend.app.auth.clerk import get_current_user
from backend.app.services.threat_intel_service import enrich_ip, enrich_domain, enrich_hash, get_threat_summary

router = APIRouter()


class ThreatIntelRequest(BaseModel):
    ip: Optional[str] = None
    domain: Optional[str] = None
    file_hash: Optional[str] = None


@router.post(
    "/enrich",
    status_code=status.HTTP_200_OK,
    summary="Enrich threat indicators with intelligence data",
)
async def enrich_threat_intel(
    request: ThreatIntelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Enrich IP addresses, domains, and file hashes with threat intelligence."""
    indicators = []
    results: Dict[str, Any] = {}

    if request.ip:
        results["ip"] = await enrich_ip(request.ip)
        indicators.append({"type": "ip", "value": request.ip})

    if request.domain:
        results["domain"] = await enrich_domain(request.domain)
        indicators.append({"type": "domain", "value": request.domain})

    if request.file_hash:
        results["hash"] = await enrich_hash(request.file_hash)
        indicators.append({"type": "hash", "value": request.file_hash})

    if not indicators:
        return {"message": "No indicators provided", "results": {}}

    summary = await get_threat_summary(indicators)
    results["summary"] = summary

    return results
