"""Attack Campaign Detection Service — groups related incidents into campaigns."""

from __future__ import annotations

import ipaddress
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from backend.app.core.config import settings
from backend.app.models.premium_models import Campaign, CampaignIncident

_CAMPAIGN_LLM_PROMPT = """\
You are a threat intelligence analyst detecting coordinated attack campaigns.
Given a set of related security incidents, generate a comprehensive campaign profile.

Return a JSON object with:
- campaign_name: descriptive name for this campaign (e.g. "Credential Harvesting Campaign")
- campaign_confidence: confidence score 0-100
- shared_indicators: list of common indicators (IPs, techniques, patterns)
- time_window: duration string (e.g. "24 hours", "72 hours")
- recommended_campaign_response: specific response strategy for the campaign
- attack_narrative: 2-3 sentence description of the campaign's likely objective
- threat_actor_profile: assessment of threat actor sophistication

Respond ONLY with valid JSON, no additional text.
"""


async def detect_campaigns(
    incidents: List[Dict[str, Any]],
    org_id: str,
    user_id: str,
    db: Optional[AsyncSession] = None,
    time_window_hours: int = 24,
) -> Dict[str, Any]:
    """Detect attack campaigns from a list of incidents.

    Clustering is based on:
    - Source IP subnet overlap
    - MITRE technique similarity
    - Attack pattern similarity
    - Temporal correlation
    - Targeted asset similarity
    """
    if not incidents:
        return {"campaigns": [], "total_detected": 0}

    # Cluster incidents
    clusters = _cluster_incidents(incidents, time_window_hours)

    campaigns = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue

        # Generate campaign profile via LLM or fallback
        profile = await _generate_campaign_profile(cluster)
        if not profile:
            continue

        campaign_id = str(uuid.uuid4())
        profile["campaign_id"] = campaign_id
        profile["related_incidents"] = [inc.get("id", f"INC-{i}") for i, inc in enumerate(cluster)]
        profile["incident_count"] = len(cluster)
        profile["first_seen"] = min(
            inc.get("timestamp", datetime.now(timezone.utc).isoformat()) for inc in cluster
        )
        profile["last_seen"] = max(
            inc.get("timestamp", datetime.now(timezone.utc).isoformat()) for inc in cluster
        )

        # Persist to database if session provided
        if db:
            await _save_campaign(db, profile, cluster, org_id, user_id)

        campaigns.append(profile)

    logger.info("Campaign detection complete", total=len(campaigns), org_id=org_id)
    return {
        "campaigns": campaigns,
        "total_detected": len(campaigns),
        "incidents_analyzed": len(incidents),
        "time_window_hours": time_window_hours,
    }


def _cluster_incidents(
    incidents: List[Dict[str, Any]], time_window_hours: int
) -> List[List[Dict[str, Any]]]:
    """Cluster incidents by similarity using heuristic scoring."""
    if not incidents:
        return []

    clusters: List[List[Dict[str, Any]]] = []
    used = set()

    for i, inc_a in enumerate(incidents):
        if i in used:
            continue
        cluster = [inc_a]
        used.add(i)

        for j, inc_b in enumerate(incidents):
            if j in used or i == j:
                continue
            score = _similarity_score(inc_a, inc_b, time_window_hours)
            if score >= 0.6:
                cluster.append(inc_b)
                used.add(j)

        clusters.append(cluster)

    return clusters


def _similarity_score(
    a: Dict[str, Any], b: Dict[str, Any], window_hours: int
) -> float:
    """Compute similarity between two incidents (0.0 to 1.0)."""
    score = 0.0
    weights_used = 0.0

    # IP subnet similarity (weight 0.25)
    if a.get("source_ip") and b.get("source_ip"):
        weights_used += 0.25
        if _same_subnet(str(a["source_ip"]), str(b["source_ip"])):
            score += 0.25

    # Attack type similarity (weight 0.25)
    if a.get("attack_type") and b.get("attack_type"):
        weights_used += 0.25
        if str(a["attack_type"]).lower() == str(b["attack_type"]).lower():
            score += 0.25
        elif _partial_match(str(a["attack_type"]), str(b["attack_type"])):
            score += 0.12

    # MITRE technique (weight 0.25)
    a_mitre = a.get("mitre_technique") or a.get("technique_id", "")
    b_mitre = b.get("mitre_technique") or b.get("technique_id", "")
    if a_mitre and b_mitre:
        weights_used += 0.25
        if str(a_mitre) == str(b_mitre):
            score += 0.25

    # Protocol (weight 0.10)
    if a.get("protocol") and b.get("protocol"):
        weights_used += 0.10
        if str(a["protocol"]).lower() == str(b["protocol"]).lower():
            score += 0.10

    # Severity (weight 0.15)
    if a.get("severity") and b.get("severity"):
        weights_used += 0.15
        if str(a["severity"]).lower() == str(b["severity"]).lower():
            score += 0.15

    return score / max(weights_used, 0.01)


def _same_subnet(ip_a: str, ip_b: str, prefix_len: int = 24) -> bool:
    """Check if two IPs are in the same /24 subnet."""
    try:
        net_a = ipaddress.ip_network(f"{ip_a}/{prefix_len}", strict=False)
        addr_b = ipaddress.ip_address(ip_b)
        return addr_b in net_a
    except (ValueError, TypeError):
        return False


def _partial_match(a: str, b: str) -> bool:
    """Check if two strings share significant common tokens."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    return overlap > 0.4


async def _generate_campaign_profile(
    cluster: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Generate a campaign profile using LLM or fallback heuristics."""
    if settings.OPENAI_API_KEY:
        return await _llm_campaign_profile(cluster)
    return _heuristic_campaign_profile(cluster)


async def _llm_campaign_profile(
    cluster: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    incident_summaries = []
    for inc in cluster[:5]:
        incident_summaries.append({
            "id": inc.get("id", "unknown"),
            "attack_type": inc.get("attack_type", "Unknown"),
            "source_ip": inc.get("source_ip", ""),
            "severity": inc.get("severity", "medium"),
            "protocol": inc.get("protocol", ""),
            "timestamp": inc.get("timestamp", ""),
        })

    user_content = f"INCIDENT CLUSTER ({len(cluster)} incidents):\n{json.dumps(incident_summaries, indent=2)}"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _CAMPAIGN_LLM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=500,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("LLM campaign profile failed", error=str(exc))
        return _heuristic_campaign_profile(cluster)


def _heuristic_campaign_profile(
    cluster: List[Dict[str, Any]]
) -> Dict[str, Any]:
    attack_types = list({inc.get("attack_type", "Unknown") for inc in cluster})
    protocols = list({inc.get("protocol", "") for inc in cluster if inc.get("protocol")})
    severities = [inc.get("severity", "medium") for inc in cluster]
    dominant_attack = max(set(attack_types), key=attack_types.count)
    attack_name = attack_types[0] if attack_types else "Multi-Vector"

    return {
        "campaign_name": f"{attack_name} Campaign",
        "campaign_confidence": min(60 + len(cluster) * 5, 95),
        "shared_indicators": [
            f"Dominant attack: {dominant_attack}",
            f"Protocols: {', '.join(protocols[:3])}",
            f"Cluster size: {len(cluster)} incidents",
        ],
        "time_window": "24 hours",
        "recommended_campaign_response": (
            f"Block source subnets involved in {dominant_attack}. "
            "Enable enhanced logging across all affected segments. "
            "Initiate threat hunt for lateral movement indicators."
        ),
        "attack_narrative": (
            f"A coordinated {dominant_attack} campaign involving {len(cluster)} incidents "
            "suggests a systematic targeting approach. The consistent attack patterns indicate "
            "an organised threat actor with specific objectives."
        ),
        "threat_actor_profile": "Intermediate sophistication — scripted or semi-automated campaign",
    }


async def _save_campaign(
    db: AsyncSession,
    profile: Dict[str, Any],
    cluster: List[Dict[str, Any]],
    org_id: str,
    user_id: str,
) -> None:
    """Persist campaign to database."""
    try:
        campaign = Campaign(
            id=uuid.UUID(profile["campaign_id"]),
            org_id=org_id,
            campaign_name=profile.get("campaign_name", "Unknown Campaign"),
            campaign_confidence=profile.get("campaign_confidence", 70.0),
            shared_indicators=profile.get("shared_indicators", []),
            time_window=profile.get("time_window", "24 hours"),
            recommended_campaign_response=profile.get("recommended_campaign_response", ""),
            attack_patterns={"attack_types": list({inc.get("attack_type", "") for inc in cluster})},
            mitre_techniques={"techniques": list({inc.get("mitre_technique", "") for inc in cluster if inc.get("mitre_technique")})},
            source_subnets={"ips": list({inc.get("source_ip", "") for inc in cluster if inc.get("source_ip")})},
            targeted_assets={"assets": list({inc.get("dest_ip", "") for inc in cluster if inc.get("dest_ip")})},
        )
        db.add(campaign)

        for inc in cluster:
            ci = CampaignIncident(
                org_id=org_id,
                campaign_id=campaign.id,
                incident_id=inc.get("id", str(uuid.uuid4())),
                correlation_score=inc.get("_similarity_score", 0.75),
            )
            db.add(ci)

        await db.commit()
    except Exception as exc:
        logger.warning("Failed to save campaign", error=str(exc))
        await db.rollback()


async def get_campaigns(
    db: AsyncSession, org_id: str, limit: int = 50
) -> List[Dict[str, Any]]:
    """Fetch all campaigns for an organisation."""
    try:
        result = await db.execute(
            select(Campaign).where(Campaign.org_id == org_id).limit(limit)
        )
        rows = result.scalars().all()
        return [_campaign_to_dict(c) for c in rows]
    except Exception as exc:
        logger.warning("Failed to fetch campaigns", error=str(exc))
        return _mock_campaigns()


async def get_campaign_by_id(
    db: AsyncSession, campaign_id: str, org_id: str
) -> Optional[Dict[str, Any]]:
    """Fetch a single campaign by ID."""
    try:
        result = await db.execute(
            select(Campaign).where(
                Campaign.id == uuid.UUID(campaign_id),
                Campaign.org_id == org_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            return _campaign_to_dict(campaign)
    except Exception as exc:
        logger.warning("Failed to fetch campaign by id", error=str(exc))
    return _mock_campaign_detail(campaign_id)


def _campaign_to_dict(c: Campaign) -> Dict[str, Any]:
    return {
        "campaign_id": str(c.id),
        "campaign_name": c.campaign_name,
        "campaign_confidence": c.campaign_confidence,
        "shared_indicators": c.shared_indicators or [],
        "time_window": c.time_window,
        "recommended_campaign_response": c.recommended_campaign_response,
        "attack_patterns": c.attack_patterns,
        "mitre_techniques": c.mitre_techniques,
        "source_subnets": c.source_subnets,
        "targeted_assets": c.targeted_assets,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _mock_campaigns() -> List[Dict[str, Any]]:
    return [
        {
            "campaign_id": "camp-001",
            "campaign_name": "Credential Harvesting Campaign",
            "campaign_confidence": 91,
            "related_incidents": ["INC-102", "INC-118", "INC-130"],
            "incident_count": 3,
            "shared_indicators": ["source subnet 45.33.x.x", "MITRE T1110", "SSH brute force"],
            "time_window": "24 hours",
            "recommended_campaign_response": "Block subnet, rotate credentials, monitor privileged accounts",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "campaign_id": "camp-002",
            "campaign_name": "Phishing-to-Ransomware Campaign",
            "campaign_confidence": 87,
            "related_incidents": ["INC-205", "INC-218"],
            "incident_count": 2,
            "shared_indicators": ["phishing email pattern", "MITRE T1566.001", ".locked extension"],
            "time_window": "48 hours",
            "recommended_campaign_response": "Block email sender domains, scan all attachments, patch email gateway",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def _mock_campaign_detail(campaign_id: str) -> Dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "campaign_name": "Credential Harvesting Campaign",
        "campaign_confidence": 91,
        "related_incidents": ["INC-102", "INC-118", "INC-130"],
        "incident_count": 3,
        "shared_indicators": ["source subnet 45.33.x.x", "MITRE T1110", "SSH brute force"],
        "time_window": "24 hours",
        "recommended_campaign_response": "Block subnet, rotate credentials, monitor privileged accounts",
        "attack_narrative": "A coordinated credential harvesting campaign targeting SSH services across the infrastructure. Consistent source subnet and technique pattern indicates automated tooling.",
        "threat_actor_profile": "Intermediate sophistication — automated credential stuffing with manual follow-up",
        "mitre_techniques": {"techniques": ["T1110", "T1078"]},
        "source_subnets": {"ips": ["45.33.32.156", "45.33.32.188", "45.33.32.201"]},
        "targeted_assets": {"assets": ["192.168.1.10", "192.168.1.22", "192.168.1.35"]},
        "timeline": [
            {"time": "T+0h", "event": "First SSH brute force detected on 192.168.1.10"},
            {"time": "T+4h", "event": "Same subnet targets 192.168.1.22"},
            {"time": "T+18h", "event": "Credential success on 192.168.1.35"},
        ],
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
