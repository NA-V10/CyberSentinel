"""MITRE ATT&CK mapping service for CyberSentinel AI."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from loguru import logger

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# MITRE ATT&CK knowledge base
# ---------------------------------------------------------------------------

MITRE_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "Brute Force": {
        "tactic": "Credential Access",
        "technique": "Brute Force",
        "technique_id": "T1110",
        "attack_category": "Credential-Based Attack",
        "confidence": 0.95,
        "sub_techniques": ["T1110.001 (Password Guessing)", "T1110.003 (Password Spraying)"],
        "recommended_mitigation": (
            "1. Implement account lockout policies (max 5 attempts). "
            "2. Enable MFA on all privileged accounts. "
            "3. Deploy fail2ban or equivalent rate limiting. "
            "4. Use CAPTCHA on public-facing login forms. "
            "5. Monitor and alert on repeated authentication failures. "
            "6. Consider IP allowlisting for admin SSH access."
        ),
    },
    "DDoS": {
        "tactic": "Impact",
        "technique": "Network Denial of Service",
        "technique_id": "T1498",
        "attack_category": "Availability Attack",
        "confidence": 0.95,
        "sub_techniques": ["T1498.001 (Direct Network Flood)", "T1498.002 (Reflection Amplification)"],
        "recommended_mitigation": (
            "1. Activate upstream DDoS scrubbing / CDN protection (Cloudflare, AWS Shield). "
            "2. Implement rate limiting at the network edge. "
            "3. Use anycast routing to distribute attack traffic. "
            "4. Block source IPs at firewall. "
            "5. Contact ISP for upstream filtering. "
            "6. Enable SYN cookies for TCP flood protection."
        ),
    },
    "Phishing": {
        "tactic": "Initial Access",
        "technique": "Phishing",
        "technique_id": "T1566",
        "attack_category": "Social Engineering",
        "confidence": 0.92,
        "sub_techniques": ["T1566.001 (Spearphishing Attachment)", "T1566.002 (Spearphishing Link)"],
        "recommended_mitigation": (
            "1. Deploy email security gateway with sandboxing (Proofpoint, Mimecast). "
            "2. Enable DMARC, DKIM, SPF on all domains. "
            "3. Block macro execution in Office documents. "
            "4. Conduct phishing awareness training. "
            "5. Implement DNS filtering to block malicious URLs. "
            "6. Isolate affected mailboxes and revoke sessions."
        ),
    },
    "Malware": {
        "tactic": "Execution",
        "technique": "Command and Scripting Interpreter",
        "technique_id": "T1059",
        "attack_category": "Malicious Code Execution",
        "confidence": 0.88,
        "sub_techniques": ["T1059.001 (PowerShell)", "T1059.003 (Windows Command Shell)", "T1547 (Boot/Logon Autostart)"],
        "recommended_mitigation": (
            "1. Isolate infected endpoint immediately from network. "
            "2. Run full EDR scan (CrowdStrike, SentinelOne). "
            "3. Identify and terminate malicious processes. "
            "4. Block C2 IP/domain at firewall and DNS. "
            "5. Forensically image the system before remediation. "
            "6. Rotate credentials from potentially compromised accounts. "
            "7. Patch exploited vulnerabilities."
        ),
    },
    "Port Scan": {
        "tactic": "Discovery",
        "technique": "Network Service Discovery",
        "technique_id": "T1046",
        "attack_category": "Reconnaissance",
        "confidence": 0.90,
        "sub_techniques": ["T1595.001 (Scanning IP Blocks)", "T1046 (Network Service Scanning)"],
        "recommended_mitigation": (
            "1. Block scanning source IP at perimeter firewall. "
            "2. Enable port scan detection in IDS/IPS. "
            "3. Audit and close unnecessary open ports. "
            "4. Implement network segmentation. "
            "5. Alert SOC team for investigation of reconnaissance activity. "
            "6. Review firewall rules and reduce attack surface."
        ),
    },
    "SQL Injection": {
        "tactic": "Initial Access",
        "technique": "Exploit Public-Facing Application",
        "technique_id": "T1190",
        "attack_category": "Web Application Attack",
        "confidence": 0.93,
        "sub_techniques": ["T1190 (Exploit Public-Facing Application)", "T1078 (Valid Accounts via credential dump)"],
        "recommended_mitigation": (
            "1. Immediately block the attacking IP at WAF. "
            "2. Apply parameterized queries / prepared statements to all DB calls. "
            "3. Enable WAF rules for SQL injection patterns. "
            "4. Audit database access logs for data exfiltration. "
            "5. Reset database credentials if compromise suspected. "
            "6. Run SAST tools to identify additional vulnerable endpoints. "
            "7. Implement input validation and output encoding."
        ),
    },
    "XSS": {
        "tactic": "Collection",
        "technique": "Browser Session Hijacking",
        "technique_id": "T1185",
        "attack_category": "Web Application Attack",
        "confidence": 0.88,
        "sub_techniques": ["T1185 (Browser Session Hijacking)", "T1190 (Exploit Public-Facing Application)"],
        "recommended_mitigation": (
            "1. Implement Content Security Policy (CSP) headers. "
            "2. Enable HttpOnly and Secure flags on session cookies. "
            "3. Apply output encoding for all user-controlled data. "
            "4. Deploy WAF with XSS detection rules. "
            "5. Invalidate affected user sessions. "
            "6. Conduct code review for unsanitized input rendering. "
            "7. Implement SameSite cookie attribute."
        ),
    },
    "Ransomware": {
        "tactic": "Impact",
        "technique": "Data Encrypted for Impact",
        "technique_id": "T1486",
        "attack_category": "Destructive Attack",
        "confidence": 0.97,
        "sub_techniques": ["T1486 (Data Encrypted for Impact)", "T1490 (Inhibit System Recovery)"],
        "recommended_mitigation": (
            "1. IMMEDIATELY isolate all affected systems from network. "
            "2. Do NOT pay ransom — contact FBI/CISA. "
            "3. Activate incident response retainer. "
            "4. Restore from clean backups (verify integrity first). "
            "5. Identify and patch the initial attack vector. "
            "6. Reset all credentials enterprise-wide. "
            "7. Notify legal, compliance, and cyber insurance carrier."
        ),
    },
    "Unauthorized Access": {
        "tactic": "Defense Evasion",
        "technique": "Valid Accounts",
        "technique_id": "T1078",
        "attack_category": "Privilege Abuse",
        "confidence": 0.85,
        "sub_techniques": ["T1078.002 (Domain Accounts)", "T1078.004 (Cloud Accounts)"],
        "recommended_mitigation": (
            "1. Immediately revoke compromised credentials. "
            "2. Enable MFA on all accounts. "
            "3. Review and audit privileged account access logs. "
            "4. Implement just-in-time (JIT) access provisioning. "
            "5. Deploy UEBA to detect anomalous account behavior. "
            "6. Enforce principle of least privilege."
        ),
    },
    "Data Exfiltration": {
        "tactic": "Exfiltration",
        "technique": "Exfiltration Over C2 Channel",
        "technique_id": "T1041",
        "attack_category": "Data Theft",
        "confidence": 0.87,
        "sub_techniques": ["T1041 (Exfiltration Over C2 Channel)", "T1048 (Exfiltration Over Alternative Protocol)"],
        "recommended_mitigation": (
            "1. Block egress to suspicious IPs/domains at firewall. "
            "2. Implement DLP (Data Loss Prevention) policies. "
            "3. Review and restrict outbound data transfer limits. "
            "4. Enable network traffic analysis for large transfers. "
            "5. Isolate systems involved in the exfiltration. "
            "6. Notify data privacy officer for potential breach reporting."
        ),
    },
    "Benign": {
        "tactic": "N/A",
        "technique": "Normal Traffic",
        "technique_id": "N/A",
        "attack_category": "Normal Activity",
        "confidence": 0.99,
        "sub_techniques": [],
        "recommended_mitigation": "No action required — traffic classified as benign.",
    },
}

_FALLBACK = {
    "tactic": "Defense Evasion",
    "technique": "Masquerading",
    "technique_id": "T1036",
    "attack_category": "Unknown Threat",
    "confidence": 0.30,
    "sub_techniques": [],
    "recommended_mitigation": "Investigate further — unknown attack pattern detected.",
}


# ---------------------------------------------------------------------------
# Public mapping function
# ---------------------------------------------------------------------------


async def map_attack(
    attack_type: str,
    incident_text: str = "",
    incident_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Map an attack type to MITRE ATT&CK framework.

    Returns a dict with tactic, technique, technique_id, attack_category,
    confidence, reasoning, recommended_mitigation.
    """
    normalized = _normalize_attack_type(attack_type)
    base = MITRE_KNOWLEDGE.get(normalized, _FALLBACK).copy()

    reasoning = await _generate_reasoning(attack_type, incident_text, base)

    result = {
        "attack_type": attack_type,
        "tactic": base["tactic"],
        "technique": base["technique"],
        "technique_id": base["technique_id"],
        "attack_category": base["attack_category"],
        "confidence": base["confidence"],
        "sub_techniques": base.get("sub_techniques", []),
        "recommended_mitigation": base["recommended_mitigation"],
        "reasoning": reasoning,
        "incident_id": incident_id,
        "org_id": org_id,
    }

    logger.info(
        "MITRE mapping complete",
        attack_type=attack_type,
        technique_id=base["technique_id"],
        confidence=base["confidence"],
    )
    return result


def _normalize_attack_type(attack_type: str) -> str:
    mapping = {
        "bruteforce": "Brute Force",
        "brute force": "Brute Force",
        "brute_force": "Brute Force",
        "ddos": "DDoS",
        "dos": "DDoS",
        "phishing": "Phishing",
        "malware": "Malware",
        "ransomware": "Ransomware",
        "portscan": "Port Scan",
        "port scan": "Port Scan",
        "port_scan": "Port Scan",
        "sql injection": "SQL Injection",
        "sqli": "SQL Injection",
        "xss": "XSS",
        "cross-site scripting": "XSS",
        "unauthorized access": "Unauthorized Access",
        "data exfiltration": "Data Exfiltration",
        "benign": "Benign",
        "normal": "Benign",
    }
    lower = attack_type.lower().strip()
    return mapping.get(lower, attack_type)


async def _generate_reasoning(
    attack_type: str, incident_text: str, base: Dict[str, Any]
) -> str:
    """Generate LLM reasoning for the MITRE mapping, with fallback."""
    default_reasoning = (
        f"This incident has been mapped to MITRE ATT&CK technique {base.get('technique_id', 'N/A')} "
        f"({base.get('technique', 'Unknown')}) under the {base.get('tactic', 'Unknown')} tactic. "
        f"Attack pattern '{attack_type}' closely matches this technique's behavioral indicators "
        f"including {', '.join(base.get('sub_techniques', ['standard attack patterns'])[:2])}."
    )

    if not settings.OPENAI_API_KEY or not incident_text:
        return default_reasoning

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = (
            f"You are a MITRE ATT&CK expert. Given this cybersecurity incident:\n\n"
            f"INCIDENT: {incident_text[:500]}\n\n"
            f"MAPPED TO: {base['tactic']} → {base['technique']} ({base['technique_id']})\n\n"
            f"In 2-3 sentences, explain WHY this mapping is correct based on the incident details. "
            f"Be specific and technical."
        )
        resp = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return resp.choices[0].message.content or default_reasoning
    except Exception as exc:
        logger.warning("MITRE LLM reasoning failed — using default", error=str(exc))
        return default_reasoning


async def persist_mapping(mapping: Dict[str, Any]) -> Optional[str]:
    """Persist a MITRE mapping to the database. Returns the created record ID."""
    try:
        import uuid as _uuid
        from backend.app.core.database import AsyncSessionLocal
        from backend.app.models.incident import MITREMapping

        incident_id = mapping.get("incident_id")
        record = MITREMapping(
            incident_id=_uuid.UUID(incident_id) if incident_id else None,
            org_id=mapping.get("org_id"),
            tactic=mapping.get("tactic"),
            technique=mapping.get("technique"),
            technique_id=mapping.get("technique_id"),
            attack_category=mapping.get("attack_category"),
            confidence=mapping.get("confidence"),
            reasoning=mapping.get("reasoning"),
            recommended_mitigation=mapping.get("recommended_mitigation"),
        )
        async with AsyncSessionLocal() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return str(record.id)
    except Exception as exc:
        logger.warning("Failed to persist MITRE mapping", error=str(exc))
        return None
