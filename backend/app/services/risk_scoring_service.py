"""Explainable risk scoring engine for CyberSentinel AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------

_SEVERITY_SCORES: Dict[str, int] = {
    "critical": 35,
    "high": 25,
    "medium": 15,
    "low": 5,
    "info": 2,
}

_ATTACK_TYPE_SCORES: Dict[str, int] = {
    "Ransomware": 25,
    "DDoS": 20,
    "Malware": 20,
    "Unauthorized Access": 18,
    "Data Exfiltration": 18,
    "SQL Injection": 15,
    "Brute Force": 15,
    "Phishing": 12,
    "XSS": 10,
    "Port Scan": 5,
    "Benign": 0,
}

_ASSET_CRITICALITY_SCORES: Dict[str, int] = {
    "critical": 10,
    "high": 7,
    "medium": 3,
    "low": 1,
}

_RISK_LEVELS = [
    (80, "critical"),
    (60, "high"),
    (35, "medium"),
    (0, "low"),
]

_MITRE_RISK_SCORES: Dict[str, int] = {
    "T1486": 10,  # Ransomware
    "T1498": 9,   # DDoS
    "T1059": 8,   # Malware execution
    "T1566": 7,   # Phishing
    "T1190": 7,   # SQLi / exploit
    "T1110": 6,   # Brute force
    "T1078": 6,   # Valid accounts
    "T1046": 3,   # Port scan
    "T1185": 5,   # XSS
    "T1041": 8,   # Exfiltration
}


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------


async def calculate_risk_score(
    severity: str,
    attack_type: str,
    source_ip: Optional[str] = None,
    model_confidence: float = 0.0,
    frequency: int = 1,
    asset_criticality: str = "medium",
    technique_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate an explainable risk score (0-100) for a cybersecurity incident.

    Returns
    -------
    dict
        risk_score (0-100), risk_level, factors list, summary.
    """
    factors: List[Dict[str, Any]] = []
    total_score = 0

    # --- Severity ---
    sev_score = _SEVERITY_SCORES.get(severity.lower(), 5)
    total_score += sev_score
    factors.append({
        "factor": f"Severity: {severity.capitalize()}",
        "impact": f"+{sev_score}",
        "reason": f"Severity level '{severity}' contributes {sev_score} base risk points.",
    })

    # --- Attack type ---
    normalized_attack = attack_type
    for k in _ATTACK_TYPE_SCORES:
        if k.lower() == attack_type.lower():
            normalized_attack = k
            break
    at_score = _ATTACK_TYPE_SCORES.get(normalized_attack, 8)
    if at_score > 0:
        total_score += at_score
        factors.append({
            "factor": f"Attack Type: {attack_type}",
            "impact": f"+{at_score}",
            "reason": f"'{attack_type}' attacks carry inherent risk weight of {at_score}.",
        })

    # --- Model confidence bonus ---
    if model_confidence >= 0.9:
        conf_bonus = 5
        total_score += conf_bonus
        factors.append({
            "factor": "High Model Confidence",
            "impact": f"+{conf_bonus}",
            "reason": f"ML classifier confidence {model_confidence:.0%} — high certainty increases score.",
        })
    elif model_confidence >= 0.7:
        conf_bonus = 3
        total_score += conf_bonus
        factors.append({
            "factor": "Moderate Model Confidence",
            "impact": f"+{conf_bonus}",
            "reason": f"ML classifier confidence {model_confidence:.0%} — moderate certainty.",
        })

    # --- Frequency ---
    if frequency > 10:
        freq_bonus = 10
        total_score += freq_bonus
        factors.append({
            "factor": "High Attack Frequency",
            "impact": f"+{freq_bonus}",
            "reason": f"Incident occurred {frequency}+ times — persistent campaign detected.",
        })
    elif frequency > 5:
        freq_bonus = 5
        total_score += freq_bonus
        factors.append({
            "factor": "Elevated Attack Frequency",
            "impact": f"+{freq_bonus}",
            "reason": f"Incident occurred {frequency} times — recurring pattern.",
        })

    # --- Source IP reputation ---
    if source_ip:
        try:
            from backend.app.services.threat_intel_service import enrich_ip
            intel = await enrich_ip(source_ip)
            if intel.get("is_malicious"):
                ip_bonus = 15
                total_score += ip_bonus
                actor = intel.get("known_threat_actor")
                actor_str = f" (attributed to {actor})" if actor else ""
                factors.append({
                    "factor": f"Malicious Source IP: {source_ip}",
                    "impact": f"+{ip_bonus}",
                    "reason": f"Source IP flagged in threat intelligence with {intel.get('abuse_confidence_score', 0)}% abuse confidence{actor_str}.",
                })
        except Exception:
            pass

    # --- Asset criticality ---
    ac_score = _ASSET_CRITICALITY_SCORES.get(asset_criticality.lower(), 3)
    if ac_score > 0:
        total_score += ac_score
        factors.append({
            "factor": f"Asset Criticality: {asset_criticality.capitalize()}",
            "impact": f"+{ac_score}",
            "reason": f"Target asset is classified as '{asset_criticality}' criticality.",
        })

    # --- MITRE technique risk ---
    if technique_id:
        mitre_score = _MITRE_RISK_SCORES.get(technique_id, 0)
        if mitre_score > 0:
            total_score += mitre_score
            factors.append({
                "factor": f"MITRE Technique Risk: {technique_id}",
                "impact": f"+{mitre_score}",
                "reason": f"MITRE ATT&CK technique {technique_id} has a known severity rating of {mitre_score}/10.",
            })

    # Clamp to 100
    final_score = min(100, total_score)

    # Determine risk level
    risk_level = "low"
    for threshold, level in _RISK_LEVELS:
        if final_score >= threshold:
            risk_level = level
            break

    logger.info(
        "Risk score calculated",
        score=final_score,
        level=risk_level,
        severity=severity,
        attack_type=attack_type,
    )

    return {
        "risk_score": final_score,
        "risk_level": risk_level,
        "factors": factors,
        "max_score": 100,
        "summary": (
            f"Risk score {final_score}/100 ({risk_level.upper()}). "
            f"{len(factors)} risk factors identified."
        ),
    }
