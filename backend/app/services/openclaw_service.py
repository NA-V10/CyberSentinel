"""OpenClaw agent service for CyberSentinel AI.

OpenClaw acts as the agent orchestration layer for:
- Creating Jira tickets from incident analysis results
- Sending incident notifications via webhook (Slack-compatible)

When ``openclaw-sdk`` is installed and ``OPENCLAW_API_KEY`` is set, requests
are routed through the OpenClaw gateway which runs the jira-ticket skill.
Otherwise the service falls back to direct Jira REST API v3 calls via httpx.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from loguru import logger

from backend.app.core.config import settings


try:
    from openclaw_sdk import OpenClawClient  # type: ignore[import]
    _OPENCLAW_AVAILABLE = True
except ImportError:
    _OPENCLAW_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _adf(text: str) -> Dict[str, Any]:
    """Wrap plain text in Atlassian Document Format (required by Jira REST API v3)."""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


_SEVERITY_TO_JIRA = {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def _jira_priority(severity: str) -> str:
    return _SEVERITY_TO_JIRA.get(severity.strip().lower(), "Medium")


# ---------------------------------------------------------------------------
# OpenClaw Incident Agent
# ---------------------------------------------------------------------------

class OpenClawIncidentAgent:
    """Agent that creates Jira tickets and sends notifications for incidents.

    Instantiate per-request (stateless) — all configuration is read from
    ``settings`` at construction time.
    """

    def __init__(self) -> None:
        self._jira_base = (settings.JIRA_BASE_URL or "").rstrip("/")
        self._jira_email = settings.JIRA_EMAIL or ""
        self._jira_token = settings.JIRA_API_TOKEN or ""
        self._default_project = settings.JIRA_PROJECT_KEY or "CS"
        self._webhook_url = settings.OPENCLAW_WEBHOOK_URL or ""
        self._openclaw_key = settings.OPENCLAW_API_KEY or ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_jira_ticket(
        self,
        summary: str,
        description: str,
        severity: str,
        attack_type: Optional[str] = None,
        incident_id: Optional[str] = None,
        project_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Jira issue for a detected incident.

        Returns
        -------
        dict
            ``status``      — ``"created"`` or ``"error"``
            ``ticket_key``  — e.g. ``CS-42``
            ``ticket_url``  — full URL to the Jira issue
        """
        project = project_key or self._default_project

        if _OPENCLAW_AVAILABLE and self._openclaw_key:
            return await self._via_openclaw(
                summary=summary,
                description=description,
                severity=severity,
                attack_type=attack_type,
                incident_id=incident_id,
                project_key=project,
            )

        return await self._via_jira_api(
            summary=summary,
            description=description,
            severity=severity,
            attack_type=attack_type,
            incident_id=incident_id,
            project_key=project,
        )

    async def notify_incident(
        self,
        incident_id: str,
        summary: str,
        severity: str,
        threat_class: Optional[str] = None,
        escalation_level: Optional[str] = None,
        ticket_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a Slack-compatible webhook notification for an incident.

        Returns
        -------
        dict
            ``status``  — ``"sent"``, ``"skipped"``, or ``"error"``
            ``detail``  — human-readable status message
        """
        if not self._webhook_url:
            logger.warning("OPENCLAW_WEBHOOK_URL not set — notification skipped")
            return {"status": "skipped", "detail": "No webhook URL configured"}

        return await self._send_webhook(
            incident_id=incident_id,
            summary=summary,
            severity=severity,
            threat_class=threat_class,
            escalation_level=escalation_level,
            ticket_url=ticket_url,
        )

    # ------------------------------------------------------------------
    # OpenClaw SDK path
    # ------------------------------------------------------------------

    async def _via_openclaw(
        self,
        summary: str,
        description: str,
        severity: str,
        attack_type: Optional[str],
        incident_id: Optional[str],
        project_key: str,
    ) -> Dict[str, Any]:
        try:
            client = await OpenClawClient.connect(api_key=self._openclaw_key)
            labels = ["cybersentinel-ai"]
            if attack_type:
                labels.append(attack_type.lower().replace(" ", "-"))

            result = await client.run(
                skill="jira-ticket",
                inputs={
                    "project": project_key,
                    "summary": summary,
                    "description": description,
                    "priority": _jira_priority(severity),
                    "labels": labels,
                    "incident_id": incident_id or "",
                },
            )

            ticket_key: str = result.get("key") or result.get("ticket_key", "")
            ticket_url: str = (
                result.get("url")
                or (f"{self._jira_base}/browse/{ticket_key}" if ticket_key else "")
            )
            logger.info("Jira ticket created via OpenClaw", ticket_key=ticket_key)
            return {"status": "created", "ticket_key": ticket_key, "ticket_url": ticket_url}

        except Exception as exc:
            logger.warning(
                "OpenClaw SDK unavailable — falling back to direct Jira API",
                error=str(exc),
            )
            return await self._via_jira_api(
                summary=summary,
                description=description,
                severity=severity,
                attack_type=attack_type,
                incident_id=incident_id,
                project_key=project_key,
            )

    # ------------------------------------------------------------------
    # Direct Jira REST API v3 path (default / fallback)
    # ------------------------------------------------------------------

    async def _via_jira_api(
        self,
        summary: str,
        description: str,
        severity: str,
        attack_type: Optional[str],
        incident_id: Optional[str],
        project_key: str,
    ) -> Dict[str, Any]:
        if not (self._jira_base and self._jira_email and self._jira_token):
            return {
                "status": "error",
                "detail": (
                    "Jira credentials not configured. "
                    "Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file."
                ),
            }

        body_lines = [description]
        if incident_id:
            body_lines.insert(0, f"CyberSentinel Incident ID: {incident_id}\n")
        if attack_type:
            body_lines.append(f"\nAttack Type: {attack_type}")
        full_body = "\n".join(body_lines)

        labels = ["cybersentinel-ai"]
        if attack_type:
            labels.append(attack_type.lower().replace(" ", "-"))

        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": _adf(full_body),
                "issuetype": {"name": "Bug"},
                "priority": {"name": _jira_priority(severity)},
                "labels": labels,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._jira_base}/rest/api/3/issue",
                    json=payload,
                    auth=(self._jira_email, self._jira_token),
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

            ticket_key = data.get("key", "")
            ticket_url = f"{self._jira_base}/browse/{ticket_key}" if ticket_key else ""
            logger.info("Jira ticket created via REST API", ticket_key=ticket_key)
            return {"status": "created", "ticket_key": ticket_key, "ticket_url": ticket_url}

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            logger.error("Jira API error", status=exc.response.status_code, body=body)
            return {"status": "error", "detail": f"Jira API returned {exc.response.status_code}: {body}"}
        except Exception as exc:
            logger.error("Jira ticket creation failed", error=str(exc))
            return {"status": "error", "detail": str(exc)}

    # ------------------------------------------------------------------
    # Webhook notification
    # ------------------------------------------------------------------

    async def _send_webhook(
        self,
        incident_id: str,
        summary: str,
        severity: str,
        threat_class: Optional[str],
        escalation_level: Optional[str],
        ticket_url: Optional[str],
    ) -> Dict[str, Any]:
        _colors = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFA500",
            "low": "#00CC00",
        }
        color = _colors.get(severity.strip().lower(), "#00D4FF")

        fields = [
            {"title": "Severity", "value": severity.upper(), "short": True},
            {"title": "Escalation", "value": escalation_level or "L1", "short": True},
        ]
        if threat_class:
            fields.append({"title": "Attack Type", "value": threat_class, "short": True})
        if ticket_url:
            fields.append({"title": "Jira Ticket", "value": f"<{ticket_url}|View>", "short": False})

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": "🚨 CyberSentinel AI — Incident Alert",
                    "text": summary,
                    "fields": fields,
                    "footer": f"Incident ID: {incident_id}  •  CyberSentinel AI",
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self._webhook_url, json=payload)
                resp.raise_for_status()
            logger.info("Incident notification sent", incident_id=incident_id)
            return {"status": "sent", "detail": "Notification delivered successfully"}
        except Exception as exc:
            logger.error("Webhook notification failed", error=str(exc))
            return {"status": "error", "detail": str(exc)}
