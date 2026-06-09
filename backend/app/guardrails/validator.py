"""
Input validation and guardrails for CyberSentinel AI.

Provides:
- IP address validation (regex + ipaddress module)
- Prompt injection detection
- Incident input validation
- Output sanitization (strip accidental secrets)
- Severity normalization
"""

from __future__ import annotations

import ipaddress
import re
from typing import Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Compiled patterns (module-level for performance)
# ---------------------------------------------------------------------------

_IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
    r"|^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"  # basic IPv6 pattern
)

# Prompt-injection indicators (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(your\s+)?(previous\s+)?instructions?", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"\bDAN\b"),  # "Do Anything Now"
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(are|were)|a)\s+", re.IGNORECASE),
    re.compile(r"override\s+(safety|content|rules|guidelines|restrictions)", re.IGNORECASE),
    re.compile(r"disregard\s+(all|any|previous|your)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"print\s+(your\s+)?(initial\s+)?instructions?", re.IGNORECASE),
    re.compile(r"what\s+(are|were)\s+your\s+(original\s+)?instructions?", re.IGNORECASE),
    re.compile(r"bypass\s+(the\s+)?(filter|restriction|safety|guard)", re.IGNORECASE),
    re.compile(r"do\s+not\s+(follow|apply)\s+", re.IGNORECASE),
]

# Patterns that look like secrets — redact from output
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI-style keys
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED_API_KEY]"),
    # Generic bearer / auth tokens
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # AWS access key IDs
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    # AWS secret keys (heuristic: 40 Base64 chars after = or :)
    (re.compile(r"(?<=[=:\s])[A-Za-z0-9/+]{40}(?=[^A-Za-z0-9/+]|$)"), "[REDACTED_SECRET]"),
    # GitHub personal access tokens
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{82}"), "[REDACTED_GITHUB_PAT]"),
    # Generic passwords in key=value form
    (
        re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key)\s*[=:]\s*\S+"),
        r"\1=[REDACTED]",
    ),
    # JWT tokens (header.payload.signature)
    (
        re.compile(r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"),
        "[REDACTED_JWT]",
    ),
    # Private key blocks
    (
        re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----[\s\S]+?-----END\s+(?:RSA\s+)?PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
]

# Valid normalised severity labels.
# Canonical output is Title-Case for display; callers can .lower() for DB writes.
_SEVERITY_MAP: dict[str, str] = {
    "critical": "Critical",
    "crit": "Critical",
    "high": "High",
    "hi": "High",
    "medium": "Medium",
    "med": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "lo": "Low",
    "info": "Low",
    "informational": "Low",
    "unknown": "Unknown",
}

# Incident text length bounds
_TEXT_MIN_LEN = 10
_TEXT_MAX_LEN = 5_000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_ip_address(ip: str) -> bool:
    """Return ``True`` if *ip* is a syntactically valid IPv4 or IPv6 address.

    Uses a quick regex pre-check followed by the stdlib :mod:`ipaddress` module
    for authoritative validation.
    """
    if not ip or not isinstance(ip, str):
        return False

    ip = ip.strip()
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        pass

    # Fall back to regex for formats ipaddress may not accept (shouldn't
    # normally happen, but keeps behaviour explicit).
    return bool(_IP_REGEX.match(ip))


def detect_prompt_injection(text: str) -> bool:
    """Return ``True`` if *text* contains prompt-injection patterns.

    Checks the text against a curated list of known injection phrases and
    structural markers (e.g. ``<system>`` tags, ``[INST]`` markers).
    """
    if not text or not isinstance(text, str):
        return False

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Prompt injection detected",
                pattern=pattern.pattern,
                snippet=text[:120],
            )
            return True

    return False


def validate_incident_input(
    text: str,
    source_ip: Optional[str] = None,
    dest_ip: Optional[str] = None,
    severity: Optional[str] = None,
) -> tuple[bool, str]:
    """Validate incident input fields.

    Parameters
    ----------
    text:
        The free-text description of the incident.
    source_ip:
        Optional source IP address string.
    dest_ip:
        Optional destination IP address string.
    severity:
        Optional severity label string.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` when all checks pass, or ``(False, <reason>)`` on the
        first failing check.
    """
    # --- text checks ---
    if text is None:
        return False, "Incident text must not be None."

    if not isinstance(text, str):
        return False, "Incident text must be a string."

    stripped = text.strip()

    if len(stripped) == 0:
        return False, "Incident text must not be empty."

    if len(stripped) < _TEXT_MIN_LEN:
        return (
            False,
            f"Incident text is too short (minimum {_TEXT_MIN_LEN} characters, got {len(stripped)}).",
        )

    if len(stripped) > _TEXT_MAX_LEN:
        return (
            False,
            f"Incident text is too long (maximum {_TEXT_MAX_LEN} characters, got {len(stripped)}).",
        )

    # --- prompt injection check ---
    if detect_prompt_injection(stripped):
        return False, "Incident text contains suspected prompt-injection content."

    # --- IP validation ---
    if source_ip is not None:
        if not validate_ip_address(source_ip):
            return False, f"Invalid source IP address: '{source_ip}'."

    if dest_ip is not None:
        if not validate_ip_address(dest_ip):
            return False, f"Invalid destination IP address: '{dest_ip}'."

    # --- severity check (only if provided) ---
    if severity is not None:
        normalised = validate_severity(severity)
        if normalised == "Unknown" and severity.strip().lower() not in ("unknown", ""):
            logger.warning("Unrecognised severity value", severity=severity)
            # We still accept it (normalised to Unknown) rather than rejecting.

    return True, ""


def sanitize_output(text: str) -> str:
    """Remove accidental secret / credential patterns from *text*.

    Replaces matched patterns with a ``[REDACTED_*]`` placeholder so that
    sensitive values are never leaked in API responses or log entries.
    """
    if not text or not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    if sanitized != text:
        logger.warning("Sensitive data pattern(s) redacted from output.")

    return sanitized


def validate_severity(severity: str) -> str:
    """Normalise a severity string to one of the canonical labels.

    Canonical labels: ``Critical``, ``High``, ``Medium``, ``Low``, ``Unknown``.

    Examples
    --------
    >>> validate_severity("CRITICAL")
    'Critical'
    >>> validate_severity("med")
    'Medium'
    >>> validate_severity("garbage")
    'Unknown'
    """
    if not severity or not isinstance(severity, str):
        return "Unknown"

    key = severity.strip().lower()
    return _SEVERITY_MAP.get(key, "Unknown")
