"""Playbook generator service — response playbooks per attack type."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Hardcoded playbook templates
# ---------------------------------------------------------------------------

_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "Brute Force": {
        "priority": "urgent",
        "estimated_time_hours": 1.5,
        "containment_steps": [
            "Block the attacking source IP(s) at the perimeter firewall immediately.",
            "Temporarily lock the targeted account(s) to prevent further compromise.",
            "Enable rate limiting on the authentication endpoint (max 5 attempts / 10 min).",
            "Notify the account owner via out-of-band communication (phone/SMS).",
        ],
        "eradication_steps": [
            "Reset passwords for all targeted accounts.",
            "Audit all login attempts from the offending IP range for the past 30 days.",
            "Review privileged account list and disable unnecessary accounts.",
            "Rotate SSH keys and service account credentials if applicable.",
        ],
        "recovery_steps": [
            "Re-enable the account only after password reset and MFA enrollment confirmation.",
            "Monitor the account for 72 hours post-recovery for anomalous activity.",
            "Verify account access logs to confirm no unauthorized changes were made.",
        ],
        "prevention_steps": [
            "Enforce MFA on all user accounts, especially privileged ones.",
            "Implement account lockout policy (5 failed attempts = 15-minute lockout).",
            "Deploy Fail2Ban or equivalent for SSH and web login endpoints.",
            "Use VPN or IP allowlisting for admin/SSH access.",
            "Enable CAPTCHA on public-facing login forms.",
        ],
        "communication_steps": [
            "Notify the affected user(s) immediately.",
            "Inform the IT security team and SOC lead.",
            "If admin credentials were targeted, escalate to CISO.",
            "Document the incident in the ticketing system.",
        ],
        "escalation_steps": [
            "Escalate to L2 if multiple accounts were targeted.",
            "Escalate to L3/CISO if privileged or service accounts were compromised.",
            "Involve legal/compliance if customer data was potentially accessed.",
        ],
    },
    "DDoS": {
        "priority": "immediate",
        "estimated_time_hours": 3.0,
        "containment_steps": [
            "Activate CDN-level DDoS protection (Cloudflare, AWS Shield Advanced).",
            "Enable rate limiting and traffic scrubbing upstream.",
            "Blackhole route the most severe attack traffic at the ISP level.",
            "Enable anycast routing to distribute attack load.",
            "Notify hosting provider / ISP for upstream filtering assistance.",
        ],
        "eradication_steps": [
            "Identify attack vectors (volumetric, protocol, application layer).",
            "Block attacking IP ranges and ASNs at firewall.",
            "Tune WAF rules to filter attack signatures.",
            "Disable or scale down non-essential services to preserve bandwidth.",
        ],
        "recovery_steps": [
            "Gradually restore normal traffic once attack subsides.",
            "Monitor service performance and response times for 24 hours.",
            "Verify all systems returned to normal operational state.",
            "Remove temporary firewall blocks for legitimate IP ranges.",
        ],
        "prevention_steps": [
            "Subscribe to a DDoS mitigation service (Cloudflare, Akamai, AWS Shield).",
            "Implement traffic baseline monitoring to detect anomalies early.",
            "Configure auto-scaling to absorb volumetric spikes.",
            "Deploy BGP-based traffic diversion for large-scale attacks.",
            "Establish SLA with ISP for emergency traffic filtering.",
        ],
        "communication_steps": [
            "Notify product/engineering teams of service degradation.",
            "Post status update to status page within 15 minutes.",
            "Inform executive team if SLA breaches are imminent.",
            "Communicate ETA for resolution to stakeholders every 30 minutes.",
        ],
        "escalation_steps": [
            "Escalate to NOC/Network team immediately.",
            "Escalate to CISO if sustained attack exceeds 1 hour.",
            "Engage DDoS mitigation vendor's emergency response team.",
        ],
    },
    "Phishing": {
        "priority": "urgent",
        "estimated_time_hours": 2.0,
        "containment_steps": [
            "Quarantine the phishing email across all affected mailboxes.",
            "Block the phishing domain and sender IP at the email gateway.",
            "Identify all users who received or clicked the phishing link.",
            "Revoke active sessions for users who clicked the link.",
            "Reset credentials for potentially compromised accounts immediately.",
        ],
        "eradication_steps": [
            "Report the phishing domain to hosting provider for takedown.",
            "Submit the phishing URL to Google Safe Browsing and Microsoft SmartScreen.",
            "Scan endpoints of users who clicked the link for malware.",
            "Review email filter rules and update to block similar campaigns.",
        ],
        "recovery_steps": [
            "Re-enroll affected users with new MFA credentials.",
            "Monitor accounts for unauthorized access for 7 days.",
            "Verify no data was exfiltrated via compromised accounts.",
            "Confirm no forwarding rules or OAuth grants were added to mailboxes.",
        ],
        "prevention_steps": [
            "Implement DMARC, DKIM, and SPF for all email domains.",
            "Deploy email sandboxing for attachment analysis.",
            "Conduct quarterly phishing simulation and awareness training.",
            "Enable link rewriting and time-of-click URL analysis.",
            "Enforce MFA on all email accounts.",
        ],
        "communication_steps": [
            "Alert all users in the organization about the campaign.",
            "Notify the affected users with clear remediation instructions.",
            "Report to legal/compliance if PII was potentially accessed.",
            "File report with relevant authorities if warranted.",
        ],
        "escalation_steps": [
            "Escalate to L2 if credentials were harvested.",
            "Escalate to CISO if executive accounts were targeted.",
            "Involve legal if customer/patient data was compromised.",
        ],
    },
    "Malware": {
        "priority": "immediate",
        "estimated_time_hours": 4.0,
        "containment_steps": [
            "Immediately isolate the infected endpoint(s) from the network (quarantine VLAN or physical disconnect).",
            "Block all C2 IPs and domains at the firewall and DNS level.",
            "Disable the affected user account(s) temporarily.",
            "Preserve system state: memory dump and disk image before remediation.",
            "Identify all systems the malware may have laterally moved to.",
        ],
        "eradication_steps": [
            "Run full EDR scan on the infected system (CrowdStrike, SentinelOne, Defender).",
            "Identify the malware family and IoCs using sandbox analysis.",
            "Remove all malware artifacts, scheduled tasks, and persistence mechanisms.",
            "Patch the exploited vulnerability that enabled initial infection.",
            "Scan all connected systems for lateral movement.",
        ],
        "recovery_steps": [
            "Reimage the infected system from a known-good baseline.",
            "Restore data from verified clean backups.",
            "Re-join the system to the domain only after full verification.",
            "Monitor the recovered system for 72 hours for recurrence.",
        ],
        "prevention_steps": [
            "Deploy EDR on all endpoints with real-time protection enabled.",
            "Implement application allowlisting.",
            "Disable macros in Office documents from the internet.",
            "Enable email attachment sandboxing.",
            "Keep all systems patched and up to date.",
            "Implement network segmentation to limit blast radius.",
        ],
        "communication_steps": [
            "Notify the SOC lead and CISO immediately.",
            "Alert IT team for containment assistance.",
            "Notify legal/compliance if sensitive data was accessible on the infected system.",
            "Document all IoCs and share with threat intelligence team.",
        ],
        "escalation_steps": [
            "Escalate to L3 specialist if ransomware is detected.",
            "Escalate to CISO and legal if data exfiltration occurred.",
            "Engage external incident response retainer if in-house capacity is insufficient.",
        ],
    },
    "SQL Injection": {
        "priority": "urgent",
        "estimated_time_hours": 2.5,
        "containment_steps": [
            "Block the attacking IP immediately at the WAF.",
            "Enable strict SQL injection protection rules on the WAF.",
            "Temporarily take the vulnerable endpoint offline if active exploitation is confirmed.",
            "Rotate database credentials if any queries returned sensitive data.",
        ],
        "eradication_steps": [
            "Fix vulnerable code by implementing parameterized queries / prepared statements.",
            "Audit all database query code for similar vulnerabilities (SAST scan).",
            "Review database access logs for signs of data exfiltration.",
            "Remove any backdoors or web shells that may have been planted.",
        ],
        "recovery_steps": [
            "Restore the vulnerable endpoint after applying the fix.",
            "Run penetration test to verify the fix is effective.",
            "Monitor database audit logs for 48 hours post-fix.",
        ],
        "prevention_steps": [
            "Use ORM or parameterized queries for ALL database interactions.",
            "Implement WAF with OWASP CRS rule set.",
            "Conduct regular DAST/SAST security scans.",
            "Apply principle of least privilege for database accounts.",
            "Enable database activity monitoring (DAM).",
        ],
        "communication_steps": [
            "Notify the application development team immediately.",
            "Escalate to CISO if PII or sensitive data was accessed.",
            "Notify data protection officer for potential GDPR/compliance reporting.",
        ],
        "escalation_steps": [
            "Escalate to L2 if data was exfiltrated.",
            "Escalate to legal/compliance for breach notification requirements.",
        ],
    },
    "Port Scan": {
        "priority": "normal",
        "estimated_time_hours": 0.5,
        "containment_steps": [
            "Block the scanning source IP at the perimeter firewall.",
            "Enable IDS/IPS rules to detect and block further scans.",
            "Review exposed services and close unnecessary ports.",
        ],
        "eradication_steps": [
            "Audit firewall rules to remove unnecessary open ports.",
            "Verify no sensitive services are inadvertently exposed to the internet.",
            "Check for any vulnerable services discovered during the scan.",
        ],
        "recovery_steps": [
            "No recovery actions needed unless exploitation followed.",
            "Continue monitoring for follow-up exploitation attempts.",
        ],
        "prevention_steps": [
            "Implement network segmentation and zero-trust architecture.",
            "Use port knocking for sensitive services.",
            "Regularly audit and reduce the attack surface.",
            "Enable geo-blocking for administrative services.",
        ],
        "communication_steps": [
            "Log the incident for tracking purposes.",
            "Alert SOC team for awareness.",
        ],
        "escalation_steps": [
            "Escalate if exploitation attempts follow the scan.",
            "Escalate to L2 if scan targets critical infrastructure.",
        ],
    },
    "XSS": {
        "priority": "urgent",
        "estimated_time_hours": 2.0,
        "containment_steps": [
            "Block the attacking IP at the WAF.",
            "Enable strict XSS protection rules on the WAF.",
            "Invalidate all active user sessions on the affected application.",
            "Remove any malicious scripts injected into the application.",
        ],
        "eradication_steps": [
            "Fix vulnerable code by implementing proper output encoding.",
            "Add Content Security Policy (CSP) headers.",
            "Enable HttpOnly and Secure flags on session cookies.",
            "Scan codebase for all instances of unescaped user input in templates.",
        ],
        "recovery_steps": [
            "Re-deploy fixed application after code review.",
            "Run automated XSS scanner to verify the fix.",
            "Monitor user session anomalies for 48 hours.",
        ],
        "prevention_steps": [
            "Implement CSP headers across all pages.",
            "Use a modern framework with automatic XSS escaping (React, Angular, Vue).",
            "Enable input validation on all user-supplied data.",
            "Deploy WAF with OWASP XSS rules.",
        ],
        "communication_steps": [
            "Notify the development team and security team.",
            "Inform affected users if their sessions were potentially hijacked.",
        ],
        "escalation_steps": [
            "Escalate to L2 if stored XSS affected multiple users.",
            "Escalate to legal if account takeovers occurred.",
        ],
    },
    "Benign": {
        "priority": "low",
        "estimated_time_hours": 0.0,
        "containment_steps": ["No containment actions required — traffic is benign."],
        "eradication_steps": ["No eradication actions required."],
        "recovery_steps": ["No recovery actions required."],
        "prevention_steps": ["Continue routine monitoring."],
        "communication_steps": ["Log the incident for audit trail."],
        "escalation_steps": ["No escalation required."],
    },
}

_DEFAULT_PLAYBOOK = {
    "priority": "urgent",
    "estimated_time_hours": 2.0,
    "containment_steps": [
        "Isolate affected systems from the network.",
        "Block the attacking IP at the firewall.",
        "Preserve evidence for forensic analysis.",
    ],
    "eradication_steps": [
        "Investigate root cause of the incident.",
        "Remove malicious artifacts.",
        "Patch the exploited vulnerability.",
    ],
    "recovery_steps": [
        "Restore affected systems from clean backups.",
        "Monitor for recurrence for 72 hours.",
    ],
    "prevention_steps": [
        "Implement additional security controls.",
        "Review and update security policies.",
    ],
    "communication_steps": [
        "Notify security team and management.",
        "Document findings.",
    ],
    "escalation_steps": [
        "Escalate to senior analyst if impact is severe.",
    ],
}


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


async def generate_playbook(
    attack_type: str,
    severity: str,
    incident_text: str = "",
    source_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a response playbook for an incident.

    Returns a structured playbook with containment, eradication, recovery,
    prevention, communication, and escalation steps.
    """
    normalized = attack_type
    for k in _PLAYBOOKS:
        if k.lower() == attack_type.lower():
            normalized = k
            break

    base = _PLAYBOOKS.get(normalized, _DEFAULT_PLAYBOOK).copy()

    # Add IP-specific steps if we have source IP
    if source_ip and attack_type.lower() not in ("benign", "port scan"):
        base["containment_steps"] = [
            f"Immediately block source IP {source_ip} at all perimeter firewalls.",
            *base["containment_steps"],
        ]

    # Elevate priority for critical severity
    if severity.lower() == "critical" and base["priority"] != "immediate":
        base["priority"] = "immediate"

    playbook = {
        "attack_type": attack_type,
        "severity": severity,
        **base,
        "total_steps": (
            len(base.get("containment_steps", [])) +
            len(base.get("eradication_steps", [])) +
            len(base.get("recovery_steps", [])) +
            len(base.get("prevention_steps", [])) +
            len(base.get("communication_steps", [])) +
            len(base.get("escalation_steps", []))
        ),
    }

    logger.info("Playbook generated", attack_type=attack_type, severity=severity, priority=base.get("priority"))
    return playbook
