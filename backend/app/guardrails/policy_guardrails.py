"""Policy-aware guardrails — extends basic validation with comprehensive security policies."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from loguru import logger

# ---------------------------------------------------------------------------
# Offensive cyber patterns — BLOCKED
# ---------------------------------------------------------------------------

_OFFENSIVE_PATTERNS: List[re.Pattern] = [
    # Malware creation
    re.compile(r"(create|write|generate|build|make)\s+(a\s+)?(malware|ransomware|virus|trojan|rootkit|keylogger|spyware|worm)", re.IGNORECASE),
    re.compile(r"(code|script|program)\s+(for|to)\s+(hack|attack|infect|exploit)", re.IGNORECASE),
    # Credential theft
    re.compile(r"(steal|extract|dump|harvest|grab)\s+(credential|password|hash|token|secret|key)", re.IGNORECASE),
    re.compile(r"(mimikatz|credential\s+dump|lsass\s+dump|pass.the.hash)", re.IGNORECASE),
    # Offensive tools
    re.compile(r"(how\s+to\s+use|run|deploy|install)\s+(metasploit|cobalt\s+strike|empire|covenant|sliver)\s+(to\s+attack)", re.IGNORECASE),
    # Exploit development
    re.compile(r"(write|create|develop|build)\s+(an?\s+)?(0day|zero.day|exploit)\s+(for|against)", re.IGNORECASE),
    re.compile(r"(buffer\s+overflow|rop\s+chain|shellcode)\s+(that\s+)?(attack|exploit|compromise|hack)", re.IGNORECASE),
    # Active attack instructions (differentiate from defense)
    re.compile(r"how\s+to\s+(launch|conduct|perform|execute)\s+a\s+(ddos|dos|ransomware|phishing)\s+attack", re.IGNORECASE),
    re.compile(r"help\s+me\s+(hack|attack|break\s+into|compromise|pwn)", re.IGNORECASE),
    re.compile(r"(ddos|flood)\s+(this|the)\s+(server|ip|address|website|service)", re.IGNORECASE),
    # Data exfiltration assistance
    re.compile(r"how\s+to\s+(exfiltrate|steal|extract)\s+(data|database|records)\s+(without|evading)", re.IGNORECASE),
    # System compromise
    re.compile(r"(how\s+to\s+)?(get|obtain)\s+(root|admin|system)\s+access\s+(without|bypass|evad)", re.IGNORECASE),
    re.compile(r"bypass\s+(antivirus|av|edr|endpoint|detection)", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Secret leakage patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"(sk-[a-zA-Z0-9]{48,})", re.IGNORECASE),           # OpenAI keys
    re.compile(r"(sk_live_[a-zA-Z0-9]{24,})", re.IGNORECASE),      # Stripe live keys
    re.compile(r"(AKIA[A-Z0-9]{16})", re.IGNORECASE),               # AWS access keys
    re.compile(r"(ghp_[a-zA-Z0-9]{36})", re.IGNORECASE),            # GitHub PAT
    re.compile(r"(xoxb-[0-9]+-[a-zA-Z0-9]+)", re.IGNORECASE),      # Slack bot token
    re.compile(r"password\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),  # Inline passwords
    re.compile(r"(private_key|secret_key|api_key)\s*[:=]\s*['\"][^'\"]{16,}['\"]", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Prompt injection patterns (from existing validator)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(your\s+)?instructions?", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"\bDAN\b"),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(are|were)|a)\s+", re.IGNORECASE),
    re.compile(r"override\s+(safety|content|rules|guidelines|restrictions)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# PolicyGuardrails class
# ---------------------------------------------------------------------------


class PolicyGuardrails:
    """Comprehensive policy-aware guardrails for CyberSentinel AI inputs."""

    async def validate(self, text: str) -> Dict[str, Any]:
        """Validate input text against all security policies.

        Parameters
        ----------
        text:
            The user-supplied input text to validate.

        Returns
        -------
        dict
            {passed, violations, risk_level, blocked_reason}
        """
        if not text or not text.strip():
            return {"passed": True, "violations": [], "risk_level": "safe", "blocked_reason": None}

        violations: List[str] = []
        blocked = False
        blocked_reason: str | None = None

        # 1. Prompt injection check
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                violations.append(f"Prompt injection attempt detected: '{pattern.pattern[:50]}'")
                blocked = True
                blocked_reason = "Prompt injection pattern detected. This input cannot be processed."
                break

        # 2. Offensive cyber instructions check
        if not blocked:
            for pattern in _OFFENSIVE_PATTERNS:
                if pattern.search(text):
                    violations.append(f"Offensive cyber instruction detected")
                    blocked = True
                    blocked_reason = (
                        "This input contains offensive cybersecurity instructions. "
                        "CyberSentinel AI provides DEFENSIVE guidance only."
                    )
                    break

        # 3. Secret leakage check
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                violations.append("Potential secret/credential detected in input")
                if not blocked:
                    blocked = True
                    blocked_reason = "Input appears to contain sensitive credentials or API keys. Please remove them."
                break

        # Determine risk level
        if blocked:
            risk_level = "blocked"
        elif violations:
            risk_level = "suspicious"
        else:
            risk_level = "safe"

        if violations:
            logger.warning(
                "Guardrail violation detected",
                violations=violations,
                risk_level=risk_level,
                text_preview=text[:100],
            )

        return {
            "passed": not blocked,
            "violations": violations,
            "risk_level": risk_level,
            "blocked_reason": blocked_reason,
        }


# Singleton instance
guardrails = PolicyGuardrails()
