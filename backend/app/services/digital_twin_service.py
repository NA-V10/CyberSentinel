"""AI SOC Digital Twin Simulator — generates synthetic attacks for training and demo."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Built-in Scenarios
# ---------------------------------------------------------------------------

_BUILTIN_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario-phishing",
        "name": "Phishing Campaign",
        "description": "Simulate a targeted spearphishing campaign hitting multiple users with malicious attachments.",
        "scenario_type": "phishing",
        "attack_type": "Phishing",
        "severity": "high",
        "expected_mitre_technique": "T1566.001 - Spearphishing Attachment",
        "expected_response": "Block sender domains, quarantine emails, user awareness training",
        "icon": "mail",
        "difficulty": "medium",
        "incident_count": 5,
    },
    {
        "id": "scenario-malware",
        "name": "Malware Outbreak",
        "description": "Simulate ransomware spreading laterally through the network via SMB vulnerabilities.",
        "scenario_type": "malware",
        "attack_type": "Ransomware",
        "severity": "critical",
        "expected_mitre_technique": "T1486 - Data Encrypted for Impact",
        "expected_response": "Immediate isolation, disable SMB, restore from backup",
        "icon": "bug",
        "difficulty": "hard",
        "incident_count": 8,
    },
    {
        "id": "scenario-ddos",
        "name": "DDoS Traffic Spike",
        "description": "Simulate a large-scale distributed denial of service attack targeting web infrastructure.",
        "scenario_type": "ddos",
        "attack_type": "DDoS",
        "severity": "high",
        "expected_mitre_technique": "T1498 - Network Denial of Service",
        "expected_response": "Activate DDoS protection, rate limit, scrubbing center routing",
        "icon": "zap",
        "difficulty": "medium",
        "incident_count": 3,
    },
    {
        "id": "scenario-insider",
        "name": "Insider Threat",
        "description": "Simulate a malicious insider exfiltrating sensitive data using privileged access.",
        "scenario_type": "insider",
        "attack_type": "Data Exfiltration",
        "severity": "critical",
        "expected_mitre_technique": "T1078 - Valid Accounts",
        "expected_response": "Revoke access, preserve evidence, legal hold, HR engagement",
        "icon": "user-x",
        "difficulty": "hard",
        "incident_count": 4,
    },
    {
        "id": "scenario-bruteforce",
        "name": "SSH Brute Force",
        "description": "Simulate a coordinated SSH brute force attack targeting exposed management ports.",
        "scenario_type": "brute_force",
        "attack_type": "Brute Force",
        "severity": "medium",
        "expected_mitre_technique": "T1110 - Brute Force",
        "expected_response": "Block source IPs, enable account lockout, disable password auth",
        "icon": "key",
        "difficulty": "easy",
        "incident_count": 6,
    },
    {
        "id": "scenario-exfil",
        "name": "Data Exfiltration",
        "description": "Simulate covert data exfiltration via DNS tunneling and encrypted channels.",
        "scenario_type": "exfiltration",
        "attack_type": "Data Exfiltration",
        "severity": "critical",
        "expected_mitre_technique": "T1048 - Exfiltration Over Alternative Protocol",
        "expected_response": "Block DNS tunneling, DLP enforcement, egress traffic analysis",
        "icon": "upload",
        "difficulty": "hard",
        "incident_count": 4,
    },
]

# ---------------------------------------------------------------------------
# Scenario templates for incident generation
# ---------------------------------------------------------------------------

_SCENARIO_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "phishing": {
        "protocols": ["SMTP", "HTTP", "HTTPS"],
        "source_ips": ["23.45.67.89", "198.51.100.42", "203.0.113.15"],
        "dest_ips": ["192.168.10.{n}", "10.0.0.{n}"],
        "attack_names": ["Spearphishing Email", "Credential Harvesting Page", "Malicious Attachment"],
        "asset_types": ["Workstation", "Mail Server", "User Endpoint"],
    },
    "malware": {
        "protocols": ["SMB", "TCP", "HTTP"],
        "source_ips": ["10.0.0.{n}", "192.168.0.{n}"],
        "dest_ips": ["192.168.10.{n}", "10.0.1.{n}"],
        "attack_names": ["Ransomware Execution", "Lateral Movement", "Privilege Escalation", "File Encryption"],
        "asset_types": ["File Server", "Domain Controller", "Workstation", "Database Server"],
    },
    "ddos": {
        "protocols": ["UDP", "TCP", "ICMP", "HTTP"],
        "source_ips": ["45.{a}.{b}.{c}", "203.{a}.{b}.{c}", "185.{a}.{b}.{c}"],
        "dest_ips": ["10.0.100.1", "10.0.100.2"],
        "attack_names": ["UDP Flood", "SYN Flood", "HTTP Flood", "Amplification Attack"],
        "asset_types": ["Web Server", "Load Balancer", "API Gateway"],
    },
    "insider": {
        "protocols": ["HTTPS", "FTP", "SMB"],
        "source_ips": ["192.168.20.{n}"],
        "dest_ips": ["104.21.{n}.1", "external-storage.example.com"],
        "attack_names": ["Bulk Data Download", "Unusual Access Pattern", "After-Hours Access"],
        "asset_types": ["File Server", "Database", "Document Repository"],
    },
    "brute_force": {
        "protocols": ["SSH", "RDP", "FTP", "LDAP"],
        "source_ips": ["45.33.32.{n}", "185.220.{n}.{m}", "23.{n}.{m}.1"],
        "dest_ips": ["192.168.1.{n}", "10.0.0.{n}"],
        "attack_names": ["Password Spraying", "SSH Brute Force", "RDP Brute Force"],
        "asset_types": ["SSH Server", "VPN Gateway", "Jump Host", "Domain Controller"],
    },
    "exfiltration": {
        "protocols": ["DNS", "HTTPS", "ICMP"],
        "source_ips": ["10.0.0.{n}", "192.168.5.{n}"],
        "dest_ips": ["8.8.{n}.{n}", "external-c2.{n}.example"],
        "attack_names": ["DNS Tunneling", "C2 Communication", "Data Staging"],
        "asset_types": ["Workstation", "File Server", "Database"],
    },
}


def get_scenarios() -> List[Dict[str, Any]]:
    """Return list of all built-in simulation scenarios."""
    return _BUILTIN_SCENARIOS


async def run_scenario(
    scenario_id: str,
    org_id: str,
    user_id: str,
    ws_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Run a simulation scenario and return the results."""
    scenario = next((s for s in _BUILTIN_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise ValueError(f"Scenario '{scenario_id}' not found")

    run_id = str(uuid.uuid4())

    async def emit(event: str, data: Dict[str, Any]) -> None:
        if ws_callback:
            try:
                await ws_callback({"event": event, "data": data})
            except Exception:
                pass

    await emit("simulation_started", {
        "run_id": run_id,
        "scenario": scenario["name"],
        "incident_count": scenario.get("incident_count", 4),
    })

    # Generate synthetic incidents
    synthetic_incidents = _generate_synthetic_incidents(scenario)
    await emit("synthetic_incident_generated", {
        "count": len(synthetic_incidents),
        "scenario_type": scenario["scenario_type"],
    })

    await emit("agents_responding", {"status": "processing", "count": len(synthetic_incidents)})

    # Run agent analysis on synthetic incidents
    agent_responses = []
    for i, incident in enumerate(synthetic_incidents):
        response = await _simulate_agent_response(incident, scenario)
        agent_responses.append(response)
        await emit("simulation_analysis_completed", {
            "incident_index": i,
            "classification": response.get("classification"),
            "correct": response.get("correct"),
        })

    # Compare expected vs actual
    expected_outcomes = _build_expected_outcomes(scenario)
    actual_outcomes = _build_actual_outcomes(agent_responses)
    comparison = _compare_outcomes(expected_outcomes, actual_outcomes, agent_responses)

    await emit("expected_vs_actual_compared", {
        "accuracy_score": comparison["accuracy_score"],
        "response_quality": comparison["response_quality_score"],
    })

    result = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "status": "completed",
        "synthetic_incidents": synthetic_incidents,
        "agent_responses": agent_responses,
        "expected_outcomes": expected_outcomes,
        "actual_outcomes": actual_outcomes,
        "accuracy_score": comparison["accuracy_score"],
        "response_quality_score": comparison["response_quality_score"],
        "comparison_summary": comparison["summary"],
        "performance_breakdown": comparison["breakdown"],
        "recommendations": comparison["recommendations"],
    }

    await emit("simulation_completed", {
        "run_id": run_id,
        "accuracy_score": comparison["accuracy_score"],
    })

    logger.info(
        "Digital twin simulation complete",
        run_id=run_id,
        scenario=scenario["name"],
        accuracy=comparison["accuracy_score"],
    )
    return result


def _generate_synthetic_incidents(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate realistic synthetic incidents for a scenario."""
    tmpl = _SCENARIO_TEMPLATES.get(scenario["scenario_type"], _SCENARIO_TEMPLATES["brute_force"])
    count = scenario.get("incident_count", 4)
    incidents = []
    base_time = datetime.now(timezone.utc)

    for i in range(count):
        n = random.randint(1, 254)
        m = random.randint(1, 254)
        a, b, c = random.randint(1, 255), random.randint(1, 255), random.randint(1, 255)

        src_template = random.choice(tmpl["source_ips"])
        dst_template = random.choice(tmpl["dest_ips"])

        src_ip = src_template.format(n=n, m=m, a=a, b=b, c=c)
        dst_ip = dst_template.format(n=n, m=m, a=a, b=b, c=c) if "{" in dst_template else dst_template

        incident = {
            "id": f"SIM-{str(uuid.uuid4())[:8].upper()}",
            "timestamp": (base_time + timedelta(minutes=i * random.randint(5, 30))).isoformat(),
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "protocol": random.choice(tmpl["protocols"]),
            "attack_type": random.choice(tmpl["attack_names"]),
            "severity": scenario["severity"],
            "asset_type": random.choice(tmpl["asset_types"]),
            "expected_mitre_technique": scenario["expected_mitre_technique"],
            "expected_response": scenario["expected_response"],
            "synthetic": True,
            "scenario_id": scenario["id"],
        }
        incidents.append(incident)

    return incidents


async def _simulate_agent_response(
    incident: Dict[str, Any],
    scenario: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate an agent's response to a synthetic incident."""
    # Simulate realistic agent accuracy (85-95% for known scenarios)
    accuracy_roll = random.random()
    correct_classification = accuracy_roll > 0.12

    if correct_classification:
        classification = scenario["attack_type"]
        confidence = random.randint(82, 96)
        mitre = scenario["expected_mitre_technique"].split(" - ")[0]
    else:
        alts = ["Reconnaissance", "Lateral Movement", "Privilege Escalation", "Unknown Threat"]
        classification = random.choice(alts)
        confidence = random.randint(55, 74)
        mitre = "T0000"

    response_quality = random.randint(72, 96) if correct_classification else random.randint(45, 70)

    return {
        "incident_id": incident["id"],
        "classification": classification,
        "expected_classification": scenario["attack_type"],
        "correct": correct_classification,
        "confidence": confidence,
        "mitre_technique": mitre,
        "expected_mitre": scenario["expected_mitre_technique"],
        "response_generated": True,
        "response_quality": response_quality,
        "response_time_ms": random.randint(800, 3500),
        "mitigation_relevant": correct_classification,
        "agent_steps": ["validation", "classification", "retrieval", "mitigation", "judge"],
    }


def _build_expected_outcomes(scenario: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "attack_type": scenario["attack_type"],
        "severity": scenario["severity"],
        "mitre_technique": scenario["expected_mitre_technique"],
        "response_strategy": scenario["expected_response"],
    }


def _build_actual_outcomes(agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not agent_responses:
        return {}
    correct = sum(1 for r in agent_responses if r.get("correct", False))
    avg_confidence = sum(r.get("confidence", 0) for r in agent_responses) / len(agent_responses)
    avg_quality = sum(r.get("response_quality", 0) for r in agent_responses) / len(agent_responses)
    classifications = [r.get("classification", "Unknown") for r in agent_responses]
    most_common = max(set(classifications), key=classifications.count)
    return {
        "dominant_classification": most_common,
        "correct_count": correct,
        "total_count": len(agent_responses),
        "average_confidence": round(avg_confidence, 1),
        "average_response_quality": round(avg_quality, 1),
        "classifications": classifications,
    }


def _compare_outcomes(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    responses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not responses:
        return {
            "accuracy_score": 0,
            "response_quality_score": 0,
            "summary": "No responses generated",
            "breakdown": {},
            "recommendations": [],
        }

    correct = actual.get("correct_count", 0)
    total = actual.get("total_count", 1)
    accuracy = round((correct / total) * 100, 1)
    quality = actual.get("average_response_quality", 75)

    breakdown = {
        "classification_accuracy": accuracy,
        "average_confidence": actual.get("average_confidence", 80),
        "response_quality": quality,
        "mitre_accuracy": round(
            sum(1 for r in responses if r.get("correct", False)) / max(len(responses), 1) * 100, 1
        ),
        "correct_incidents": correct,
        "total_incidents": total,
    }

    recommendations = []
    if accuracy < 80:
        recommendations.append("Re-train classification model with more examples of this attack type")
    if quality < 75:
        recommendations.append("Improve retrieval context for similar incident scenarios")
    if actual.get("average_confidence", 80) < 75:
        recommendations.append("Increase threshold for low-confidence incidents to trigger human review")

    if accuracy >= 90:
        summary = f"Excellent performance: {accuracy}% accuracy on {total} synthetic incidents."
    elif accuracy >= 75:
        summary = f"Good performance: {accuracy}% accuracy. {total - correct} incidents misclassified."
    else:
        summary = f"Needs improvement: Only {accuracy}% accuracy. Consider model fine-tuning."

    return {
        "accuracy_score": accuracy,
        "response_quality_score": round(quality, 1),
        "summary": summary,
        "breakdown": breakdown,
        "recommendations": recommendations,
    }


async def compare_runs(
    run_ids: List[str],
    org_id: str,
) -> Dict[str, Any]:
    """Compare multiple simulation runs."""
    return {
        "run_ids": run_ids,
        "comparison": "Run comparison not yet available for these IDs",
        "note": "Store runs in DB and compare accuracy_score, response_quality_score across runs",
    }
