"""Simulation service — pre-built attack scenarios for demo mode."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "phishing-email",
        "name": "Phishing Email Campaign",
        "description": "Targeted spearphishing campaign against the HR department with credential harvesting payload.",
        "category": "Initial Access",
        "attack_type": "Phishing",
        "severity": "High",
        "source_ip": "185.220.101.47",
        "dest_ip": "192.168.1.55",
        "protocol": "SMTP",
        "tags": ["spearphishing", "credential-harvesting", "hr-target", "initial-access"],
        "incident_text": (
            "SECURITY ALERT: Targeted phishing campaign detected. Multiple HR department employees "
            "received spearphishing emails purportedly from 'IT Support <support@company-it-help.com>'. "
            "The emails contain a malicious link to a credential harvesting page mimicking the corporate "
            "Office 365 login portal. Source IP 185.220.101.47 has been flagged in multiple threat intel "
            "feeds. Three employees clicked the link. Two credentials may be compromised. "
            "Email subject: 'Urgent: Your Office 365 password expires in 24 hours'. "
            "The phishing domain company-it-help.com was registered 3 days ago."
        ),
        "packet_length": 1450,
        "flow_duration": 1200.0,
        "packet_rate": 12.5,
    },
    {
        "id": "brute-force-ssh",
        "name": "Brute Force SSH Attack",
        "description": "Persistent SSH brute force attack from a Tor exit node targeting production servers.",
        "category": "Credential Access",
        "attack_type": "Brute Force",
        "severity": "High",
        "source_ip": "104.21.23.187",
        "dest_ip": "10.0.1.50",
        "protocol": "SSH",
        "tags": ["ssh", "brute-force", "tor-exit-node", "production-server"],
        "incident_text": (
            "CRITICAL: SSH brute force attack detected against production server (10.0.1.50). "
            "Source IP 104.21.23.187 (Tor exit node) has made 8,432 failed authentication attempts "
            "in the last 15 minutes. Username wordlist includes: root, admin, ubuntu, deploy, jenkins. "
            "Current failure rate: 562 attempts/minute. "
            "The attack started at 14:23 UTC and is ongoing. "
            "SSH port 22 is publicly exposed. No MFA is configured on the target server. "
            "Two successful logins to non-privileged accounts detected at 14:35 UTC."
        ),
        "packet_length": 128,
        "flow_duration": 900.0,
        "packet_rate": 562.0,
    },
    {
        "id": "malware-infection",
        "name": "Malware Infection",
        "description": "Advanced malware with C2 communication detected on a finance workstation.",
        "category": "Execution / Persistence",
        "attack_type": "Malware",
        "severity": "Critical",
        "source_ip": "10.0.5.22",
        "dest_ip": "91.108.56.150",
        "protocol": "HTTPS",
        "tags": ["c2-communication", "finance", "data-theft", "persistence"],
        "incident_text": (
            "CRITICAL MALWARE ALERT: Advanced threat detected on finance workstation (FINANCE-WS-007). "
            "EDR detected a process injection attack at 09:15 UTC. "
            "The malware (identified as Cobalt Strike Beacon variant) is communicating with C2 server "
            "91.108.56.150:443 using HTTPS. Beacon interval: 60 seconds. "
            "Process tree: winword.exe → powershell.exe → rundll32.exe → [malicious DLL]. "
            "The infection vector appears to be a malicious macro in a finance report email attachment. "
            "The workstation has access to the corporate financial database and payroll system. "
            "Data staging behavior detected: 2.3 GB of files compressed in C:\\Temp\\backup.zip. "
            "Lateral movement attempted to CFO laptop and ERP server."
        ),
        "packet_length": 850,
        "flow_duration": 3600.0,
        "packet_rate": 1.2,
    },
    {
        "id": "ddos-spike",
        "name": "DDoS Traffic Spike",
        "description": "Volumetric DDoS attack causing service degradation across public APIs.",
        "category": "Impact",
        "attack_type": "DDoS",
        "severity": "Critical",
        "source_ip": "198.51.100.42",
        "dest_ip": "203.0.113.10",
        "protocol": "UDP",
        "tags": ["volumetric", "udp-flood", "api-degradation", "botnet"],
        "incident_text": (
            "CRITICAL DDoS ATTACK: Volumetric UDP flood attack detected. "
            "Traffic volume has spiked to 48 Gbps (baseline: 2 Gbps). "
            "Source: Distributed botnet with 12,000+ unique source IPs. "
            "Attack vector: DNS amplification using open resolvers. "
            "Target: Public API gateway (api.company.com) on 203.0.113.10. "
            "Service impact: API response times increased from 120ms to 45,000ms. "
            "Error rate: 94% of requests timing out. "
            "Customer-facing services AFFECTED: payment processing, user authentication, mobile app. "
            "Attack started at 16:45 UTC. ISP contacted. AWS Shield Advanced not yet activated."
        ),
        "packet_length": 64,
        "flow_duration": 10.0,
        "packet_rate": 18500.0,
    },
    {
        "id": "unauthorized-access",
        "name": "Unauthorized Admin Access",
        "description": "Suspicious privileged account activity with potential credential compromise.",
        "category": "Defense Evasion",
        "attack_type": "Unauthorized Access",
        "severity": "High",
        "source_ip": "203.0.113.88",
        "dest_ip": "10.0.0.1",
        "protocol": "HTTPS",
        "tags": ["privilege-escalation", "lateral-movement", "admin-account", "after-hours"],
        "incident_text": (
            "UNAUTHORIZED ACCESS ALERT: Admin account 'sysadmin@company.com' logged in from an unusual "
            "location (IP: 203.0.113.88, Country: RU) at 02:47 UTC (outside business hours). "
            "The account performed the following privileged actions in 8 minutes: "
            "1. Accessed Active Directory and enumerated 500+ user accounts. "
            "2. Created a new admin account 'backup-admin' with full domain privileges. "
            "3. Disabled antivirus on 3 servers. "
            "4. Accessed the password vault and viewed 12 service account credentials. "
            "5. Exported the HR employee database. "
            "The legitimate admin confirmed they did NOT perform these actions. "
            "Account credentials likely obtained via credential stuffing from a recent dark web dump."
        ),
        "packet_length": 1200,
        "flow_duration": 480.0,
        "packet_rate": 8.5,
    },
    {
        "id": "data-exfiltration",
        "name": "Suspicious Data Exfiltration",
        "description": "Large volume of sensitive data transferred to an external cloud storage service.",
        "category": "Exfiltration",
        "attack_type": "Data Exfiltration",
        "severity": "Critical",
        "source_ip": "10.0.8.15",
        "dest_ip": "185.199.108.153",
        "protocol": "HTTPS",
        "tags": ["data-theft", "cloud-storage", "sensitive-data", "insider-threat"],
        "incident_text": (
            "DATA EXFILTRATION ALERT: Unusual outbound data transfer detected from engineering workstation "
            "(10.0.8.15, user: j.smith@company.com). "
            "Volume: 47 GB transferred to Mega.nz (185.199.108.153) over 3 hours. "
            "Transferred data includes: source code repositories, customer PII database exports, "
            "infrastructure configuration files, and API keys. "
            "DLP system flagged 'customer_data_export_2024.zip' (12 GB) containing 450,000 customer records. "
            "The employee recently resigned with 2-week notice period. "
            "Transfer occurred during after-hours (11 PM - 2 AM). "
            "This may constitute a data breach requiring regulatory notification under GDPR/CCPA. "
            "Estimated 450,000 customer records at risk."
        ),
        "packet_length": 1400,
        "flow_duration": 10800.0,
        "packet_rate": 95.3,
    },
]

_SCENARIO_INDEX = {s["id"]: s for s in SCENARIOS}


def get_scenarios() -> List[Dict[str, Any]]:
    """Return all available simulation scenarios."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "category": s["category"],
            "attack_type": s["attack_type"],
            "severity": s["severity"],
            "tags": s["tags"],
        }
        for s in SCENARIOS
    ]


async def run_scenario(scenario_id: str, user_id: str = "demo") -> Dict[str, Any]:
    """Get the full incident data for a scenario, ready to submit for analysis."""
    scenario = _SCENARIO_INDEX.get(scenario_id)
    if not scenario:
        return {"error": f"Scenario '{scenario_id}' not found", "available": list(_SCENARIO_INDEX.keys())}

    return {
        "scenario_id": scenario_id,
        "name": scenario["name"],
        "incident_text": scenario["incident_text"],
        "source_ip": scenario["source_ip"],
        "dest_ip": scenario["dest_ip"],
        "protocol": scenario["protocol"],
        "severity": scenario["severity"].lower(),
        "attack_type": scenario["attack_type"],
        "packet_length": scenario.get("packet_length"),
        "flow_duration": scenario.get("flow_duration"),
        "packet_rate": scenario.get("packet_rate"),
        "user_id": user_id,
    }
