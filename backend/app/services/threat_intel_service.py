"""Threat intelligence enrichment service with mock connectors."""

from __future__ import annotations

import hashlib
import ipaddress
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Internal / private IP check
# ---------------------------------------------------------------------------

def _is_internal_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _deterministic_seed(value: str) -> random.Random:
    """Create a seeded Random instance for deterministic but varied mock data."""
    seed = int(hashlib.md5(value.encode()).hexdigest(), 16) % (2**31)
    return random.Random(seed)


_THREAT_ACTORS = [
    "APT28", "APT29", "Lazarus Group", "Cozy Bear", "FancyBear",
    "Sandworm", "DarkSide", "REvil", "Conti", "BlackCat", None, None, None,
]
_COUNTRIES = ["RU", "CN", "KP", "IR", "US", "DE", "NL", "UA", "BR", "IN"]
_CITIES = ["Moscow", "Beijing", "Pyongyang", "Tehran", "Amsterdam", "Frankfurt", "São Paulo"]
_ISPS = ["Akamai Technologies", "Cloudflare Inc", "DigitalOcean LLC", "OVH SAS",
         "Amazon.com Inc", "Linode LLC", "Choopa LLC", "Hetzner Online GmbH"]
_THREAT_CATEGORIES = [
    ["Malware", "Botnet"],
    ["Phishing", "Spam"],
    ["DDoS", "Amplification"],
    ["Scanner", "Brute Force"],
    ["Exploit", "Web Attack"],
    ["Ransomware"],
]

_FIRST_SEEN_OFFSET_DAYS = [30, 90, 180, 365, 720]

# ---------------------------------------------------------------------------
# IP enrichment
# ---------------------------------------------------------------------------


async def enrich_ip(ip: str) -> Dict[str, Any]:
    """Enrich an IP address with threat intelligence.

    Returns realistic mock data for demo / development purposes.
    """
    if not ip:
        return {"error": "No IP provided"}

    if _is_internal_ip(ip):
        return {
            "ip": ip,
            "is_internal": True,
            "is_malicious": False,
            "reputation_score": 100,
            "abuse_confidence_score": 0,
            "geo_country": "Internal",
            "geo_city": "Internal Network",
            "isp": "Internal",
            "threat_categories": [],
            "known_threat_actor": None,
            "first_seen": None,
            "last_seen": None,
            "total_reports": 0,
        }

    rng = _deterministic_seed(ip)
    is_malicious = rng.random() < 0.35
    reputation = rng.randint(0, 40) if is_malicious else rng.randint(60, 100)
    abuse_score = rng.randint(40, 100) if is_malicious else rng.randint(0, 15)
    country = rng.choice(_COUNTRIES)
    city = rng.choice(_CITIES)
    isp = rng.choice(_ISPS)
    threat_actor = rng.choice(_THREAT_ACTORS) if is_malicious else None
    categories = rng.choice(_THREAT_CATEGORIES) if is_malicious else []
    first_seen_days = rng.choice(_FIRST_SEEN_OFFSET_DAYS)
    last_seen_days = rng.randint(0, min(first_seen_days, 7))
    first_seen = (datetime.utcnow() - timedelta(days=first_seen_days)).strftime("%Y-%m-%d")
    last_seen = (datetime.utcnow() - timedelta(days=last_seen_days)).strftime("%Y-%m-%d")

    result = {
        "ip": ip,
        "is_internal": False,
        "is_malicious": is_malicious,
        "reputation_score": reputation,
        "abuse_confidence_score": abuse_score,
        "geo_country": country,
        "geo_city": city,
        "isp": isp,
        "threat_categories": categories,
        "known_threat_actor": threat_actor,
        "first_seen": first_seen if is_malicious else None,
        "last_seen": last_seen if is_malicious else None,
        "total_reports": rng.randint(10, 500) if is_malicious else 0,
        "asn": f"AS{rng.randint(1000, 99999)}",
    }

    logger.info("IP enrichment complete", ip=ip, is_malicious=is_malicious)
    return result


# ---------------------------------------------------------------------------
# Domain enrichment
# ---------------------------------------------------------------------------


async def enrich_domain(domain: str) -> Dict[str, Any]:
    """Enrich a domain name with threat intelligence."""
    if not domain:
        return {"error": "No domain provided"}

    rng = _deterministic_seed(domain)
    is_malicious = rng.random() < 0.25
    reputation = rng.randint(0, 40) if is_malicious else rng.randint(65, 100)
    categories = rng.choice(_THREAT_CATEGORIES) if is_malicious else ["Legitimate"]
    reg_date = (datetime.utcnow() - timedelta(days=rng.randint(30, 3650))).strftime("%Y-%m-%d")

    result = {
        "domain": domain,
        "is_malicious": is_malicious,
        "reputation_score": reputation,
        "categories": categories,
        "registrar": rng.choice(["GoDaddy", "Namecheap", "Google Domains", "Cloudflare", "Unknown"]),
        "registration_date": reg_date,
        "country": rng.choice(_COUNTRIES),
        "resolved_ips": [f"{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}"],
        "is_newly_registered": rng.random() < 0.15,
        "is_parked": rng.random() < 0.05,
        "mx_records": [] if is_malicious else [f"mail.{domain}"],
    }

    logger.info("Domain enrichment complete", domain=domain, is_malicious=is_malicious)
    return result


# ---------------------------------------------------------------------------
# File hash enrichment
# ---------------------------------------------------------------------------


async def enrich_hash(file_hash: str) -> Dict[str, Any]:
    """Enrich a file hash (MD5/SHA1/SHA256) with threat intelligence."""
    if not file_hash:
        return {"error": "No hash provided"}

    rng = _deterministic_seed(file_hash)
    is_malicious = rng.random() < 0.45
    hash_type = "SHA256" if len(file_hash) == 64 else "MD5" if len(file_hash) == 32 else "SHA1"

    result = {
        "hash": file_hash,
        "hash_type": hash_type,
        "is_malicious": is_malicious,
        "detection_count": rng.randint(20, 72) if is_malicious else 0,
        "total_scanners": 72,
        "malware_family": rng.choice(["Emotet", "Ryuk", "QBot", "Cobalt Strike", "Metasploit", None]) if is_malicious else None,
        "threat_name": f"Trojan.{rng.choice(['Win32', 'Generic', 'Agent'])}" if is_malicious else None,
        "first_submission": (datetime.utcnow() - timedelta(days=rng.randint(10, 365))).strftime("%Y-%m-%d"),
        "file_type": rng.choice(["PE32 executable", "PDF document", "Office document", "Archive"]),
        "file_size_bytes": rng.randint(10240, 5242880),
    }

    logger.info("Hash enrichment complete", hash=file_hash[:16], is_malicious=is_malicious)
    return result


# ---------------------------------------------------------------------------
# Consolidated threat summary
# ---------------------------------------------------------------------------


async def get_threat_summary(indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enrich multiple indicators and return a consolidated threat summary."""
    results = []
    overall_malicious_count = 0

    for indicator in indicators:
        ind_type = indicator.get("type", "").lower()
        value = indicator.get("value", "")

        if ind_type == "ip":
            result = await enrich_ip(value)
        elif ind_type == "domain":
            result = await enrich_domain(value)
        elif ind_type in ("hash", "md5", "sha1", "sha256"):
            result = await enrich_hash(value)
        else:
            result = {"value": value, "type": ind_type, "error": "Unknown indicator type"}

        result["indicator_type"] = ind_type
        if result.get("is_malicious"):
            overall_malicious_count += 1
        results.append(result)

    total = len(results)
    risk_level = (
        "critical" if overall_malicious_count / max(total, 1) > 0.6
        else "high" if overall_malicious_count > 0
        else "low"
    )

    return {
        "indicators": results,
        "total_indicators": total,
        "malicious_count": overall_malicious_count,
        "risk_level": risk_level,
        "summary": (
            f"{overall_malicious_count}/{total} indicators flagged as malicious. "
            f"Overall risk level: {risk_level.upper()}."
        ),
    }
