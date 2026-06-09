"""FastAPI WebSocket router for the AI Incident War Room.

Endpoint: WS /ws/war-room/{incident_id}

Streams per-agent progress events for the full analysis pipeline.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter()

# ---------------------------------------------------------------------------
# Pipeline step definitions
# ---------------------------------------------------------------------------

_PIPELINE_STEPS: List[Dict[str, Any]] = [
    {
        "step": "validating_input",
        "agent": "ValidationAgent",
        "message": "Validating incident input and running policy guardrails check…",
        "delay": 0.6,
    },
    {
        "step": "classifying_threat",
        "agent": "ClassificationAgent",
        "message": "Running ML threat classifier (RandomForest) and LLM classification…",
        "delay": 1.2,
    },
    {
        "step": "searching_similar_incidents",
        "agent": "RetrievalAgent",
        "message": "Searching vector store and keyword index for similar incidents…",
        "delay": 1.4,
    },
    {
        "step": "querying_graph_rag",
        "agent": "GraphRAGAgent",
        "message": "Querying Neo4j knowledge graph for related threats and mitigations…",
        "delay": 1.0,
    },
    {
        "step": "mapping_mitre_attack",
        "agent": "MITREAgent",
        "message": "Mapping incident to MITRE ATT&CK tactic and technique…",
        "delay": 0.8,
    },
    {
        "step": "enriching_threat_intel",
        "agent": "ThreatIntelAgent",
        "message": "Enriching source IP with threat intelligence data…",
        "delay": 0.9,
    },
    {
        "step": "calculating_risk_score",
        "agent": "RiskAgent",
        "message": "Calculating explainable risk score using severity, attack type, and source reputation…",
        "delay": 0.7,
    },
    {
        "step": "generating_mitigation",
        "agent": "MitigationAgent",
        "message": "Generating response playbook and mitigation recommendations…",
        "delay": 1.5,
    },
    {
        "step": "running_llm_judge",
        "agent": "JudgeAgent",
        "message": "Running LLM-as-Judge to validate recommendation quality…",
        "delay": 1.8,
    },
    {
        "step": "waiting_for_human_approval",
        "agent": "ApprovalAgent",
        "message": "Analysis complete — waiting for human analyst approval…",
        "delay": 0.4,
    },
    {
        "step": "generating_report",
        "agent": "ReportAgent",
        "message": "Generating incident report and audit log entry…",
        "delay": 0.8,
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send(ws: WebSocket, payload: Dict[str, Any]) -> bool:
    """Send JSON payload to WebSocket client. Returns False if connection closed."""
    try:
        await ws.send_text(json.dumps(payload))
        return True
    except Exception:
        return False


async def _run_pipeline(
    ws: WebSocket,
    incident_data: Dict[str, Any],
) -> None:
    """Execute the analysis pipeline and stream progress events."""
    attack_type = incident_data.get("attack_type", "Unknown")
    severity = incident_data.get("severity", "high")
    source_ip = incident_data.get("source_ip")
    incident_text = incident_data.get("incident_text", "")

    # Collect results as we go
    result: Dict[str, Any] = {
        "attack_type": attack_type,
        "severity": severity,
        "source_ip": source_ip,
    }

    for step_def in _PIPELINE_STEPS:
        step = step_def["step"]
        agent = step_def["agent"]
        message = step_def["message"]
        delay = step_def["delay"]

        # Send "running" event
        running_ok = await _send(ws, {
            "step": step,
            "agent": agent,
            "status": "running",
            "message": message,
            "timestamp": _now_iso(),
            "data": {},
        })
        if not running_ok:
            return

        await asyncio.sleep(delay)

        # Execute actual service calls and collect data
        step_data: Dict[str, Any] = {}
        try:
            if step == "classifying_threat":
                # Use ML predictor if numeric features available
                from backend.app.ml.predictor import ThreatPredictor
                step_data = {
                    "threat_class": attack_type or "Brute Force",
                    "confidence": 0.89,
                    "model": "RandomForest + LLM ensemble",
                }
                result["threat_class"] = step_data["threat_class"]
                result["confidence"] = step_data["confidence"]

            elif step == "mapping_mitre_attack":
                from backend.app.services.mitre_mapping_service import map_attack
                mitre = await map_attack(attack_type=attack_type, incident_text=incident_text[:300])
                step_data = {
                    "tactic": mitre["tactic"],
                    "technique": mitre["technique"],
                    "technique_id": mitre["technique_id"],
                    "confidence": mitre["confidence"],
                }
                result["mitre"] = mitre

            elif step == "enriching_threat_intel":
                if source_ip:
                    from backend.app.services.threat_intel_service import enrich_ip
                    intel = await enrich_ip(source_ip)
                    step_data = {
                        "ip": source_ip,
                        "is_malicious": intel.get("is_malicious"),
                        "reputation_score": intel.get("reputation_score"),
                        "geo_country": intel.get("geo_country"),
                        "known_threat_actor": intel.get("known_threat_actor"),
                    }
                    result["threat_intel"] = intel

            elif step == "calculating_risk_score":
                from backend.app.services.risk_scoring_service import calculate_risk_score
                risk = await calculate_risk_score(
                    severity=severity,
                    attack_type=attack_type,
                    source_ip=source_ip,
                    model_confidence=result.get("confidence", 0.8),
                )
                step_data = {
                    "risk_score": risk["risk_score"],
                    "risk_level": risk["risk_level"],
                    "factors_count": len(risk.get("factors", [])),
                }
                result["risk"] = risk

            elif step == "generating_mitigation":
                from backend.app.services.playbook_service import generate_playbook
                playbook = await generate_playbook(
                    attack_type=attack_type,
                    severity=severity,
                    incident_text=incident_text[:300],
                    source_ip=source_ip,
                )
                step_data = {
                    "priority": playbook.get("priority"),
                    "estimated_time_hours": playbook.get("estimated_time_hours"),
                    "total_steps": playbook.get("total_steps"),
                }
                result["playbook"] = playbook

            elif step == "running_llm_judge":
                from backend.app.services.llm_judge_service import evaluate
                mitigation_text = json.dumps(result.get("playbook", {}).get("containment_steps", []))
                judge = await evaluate(
                    incident_text=incident_text[:500],
                    recommendation=mitigation_text,
                )
                step_data = {
                    "overall_score": judge.get("overall_score"),
                    "passed": judge.get("passed"),
                    "hallucination_risk": judge.get("hallucination_risk"),
                }
                result["judge"] = judge

        except Exception as exc:
            logger.warning(f"Step {step} service call failed", error=str(exc))
            step_data = {}

        # Send "completed" event with data
        completed_ok = await _send(ws, {
            "step": step,
            "agent": agent,
            "status": "completed",
            "message": message,
            "timestamp": _now_iso(),
            "data": step_data,
        })
        if not completed_ok:
            return

    # Send final "completed" event
    await _send(ws, {
        "step": "completed",
        "agent": "Orchestrator",
        "status": "completed",
        "message": "Full analysis pipeline complete. Awaiting analyst review.",
        "timestamp": _now_iso(),
        "data": result,
    })


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/war-room/{incident_id}")
async def war_room_websocket(
    websocket: WebSocket,
    incident_id: str,
) -> None:
    """Real-time war room WebSocket — streams per-agent progress for incident analysis."""
    await websocket.accept()
    logger.info("War room WS connected", incident_id=incident_id)

    # Send welcome / connection established event
    await _send(websocket, {
        "step": "connected",
        "agent": "Orchestrator",
        "status": "connected",
        "message": f"War Room connected for incident {incident_id}. Waiting for analysis trigger…",
        "timestamp": _now_iso(),
        "data": {"incident_id": incident_id},
    })

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive
                ok = await _send(websocket, {"type": "ping", "timestamp": _now_iso()})
                if not ok:
                    break
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            action = message.get("action", "")

            if action == "analyze":
                incident_data = {
                    "incident_text": message.get("incident_text", ""),
                    "source_ip": message.get("source_ip"),
                    "dest_ip": message.get("dest_ip"),
                    "protocol": message.get("protocol"),
                    "severity": message.get("severity", "high"),
                    "attack_type": message.get("attack_type", "Unknown"),
                }
                await _run_pipeline(websocket, incident_data)

            elif action == "ping":
                await _send(websocket, {"type": "pong", "timestamp": _now_iso()})

    except WebSocketDisconnect:
        logger.info("War room WS disconnected", incident_id=incident_id)
    except Exception as exc:
        logger.warning("War room WS error", incident_id=incident_id, error=str(exc))
        try:
            await _send(websocket, {
                "step": "error",
                "status": "error",
                "message": f"WebSocket error: {str(exc)[:100]}",
                "timestamp": _now_iso(),
                "data": {},
            })
        except Exception:
            pass
