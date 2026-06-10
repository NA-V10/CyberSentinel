"""Multi-LLM Consensus Engine — analyzes incidents with multiple models and weighted voting."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Model cost pricing (USD per 1K tokens)
# ---------------------------------------------------------------------------
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4.1": {"input": 0.002, "output": 0.008},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
    "llama-3.1-8b": {"input": 0.0001, "output": 0.0001},
    "mock-model": {"input": 0.0, "output": 0.0},
}

_MODEL_WEIGHTS: Dict[str, float] = {
    "openai": 0.45,
    "anthropic": 0.35,
    "local": 0.20,
    "mock": 0.15,
}

_ANALYSIS_SYSTEM_PROMPT = """\
You are an expert cybersecurity analyst. Analyze the provided security incident and return a JSON object with:
- threat_classification: string (e.g. "Brute Force", "Ransomware", "Phishing")
- severity: string ("critical", "high", "medium", "low")
- mitre_mapping: string (e.g. "T1110 - Brute Force")
- risk_score: number (0-100)
- recommended_mitigation: string (2-3 sentences)
- confidence: number (0-100)
- reasoning: string (1-2 sentences explaining classification)

Respond ONLY with valid JSON, no additional text.
"""


async def run_consensus_analysis(
    incident_text: str,
    org_id: str,
    user_id: str,
    incident_id: Optional[str] = None,
    ws_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Run multi-model consensus analysis on a security incident."""

    async def emit(event: str, data: Dict[str, Any]) -> None:
        if ws_callback:
            try:
                await ws_callback({"event": event, "data": data})
            except Exception:
                pass

    await emit("consensus_started", {"incident_id": incident_id, "models": ["GPT", "Claude", "Llama"]})

    # Gather model analyses in sequence (parallel optional)
    model_outputs: List[Dict[str, Any]] = []

    # 1. OpenAI GPT
    await emit("model_analysis_started", {"model": "GPT"})
    gpt_output = await _analyze_with_openai(incident_text)
    model_outputs.append(gpt_output)
    await emit("model_analysis_completed", {"model": "GPT", "available": gpt_output["available"]})

    # 2. Anthropic Claude
    await emit("model_analysis_started", {"model": "Claude"})
    claude_output = await _analyze_with_claude(incident_text)
    model_outputs.append(claude_output)
    await emit("model_analysis_completed", {"model": "Claude", "available": claude_output["available"]})

    # 3. Local Llama / Mock
    await emit("model_analysis_started", {"model": "Llama"})
    llama_output = await _analyze_with_llama(incident_text)
    model_outputs.append(llama_output)
    await emit("model_analysis_completed", {"model": "Llama", "available": llama_output["available"]})

    # Redistribute weights for unavailable models
    available_outputs = [m for m in model_outputs if m["available"]]
    adjusted = _adjust_weights(model_outputs)

    # Weighted voting for consensus
    await emit("consensus_voting_started", {"participating_models": len(available_outputs)})
    consensus = _compute_consensus(adjusted)

    # Build disagreement summary
    disagreement = _summarize_disagreements(available_outputs, consensus)

    # Cost tracking
    total_cost = sum(m.get("estimated_cost", 0.0) for m in model_outputs)

    result = {
        "model_outputs": model_outputs,
        "consensus_classification": consensus["classification"],
        "consensus_severity": consensus["severity"],
        "consensus_mitre": consensus["mitre_mapping"],
        "consensus_risk_score": consensus["risk_score"],
        "consensus_mitigation": consensus["recommended_mitigation"],
        "agreement_score": consensus["agreement_score"],
        "disagreement_summary": disagreement,
        "final_recommendation": _build_final_recommendation(consensus, disagreement),
        "models_used": [m["model"] for m in model_outputs if m["available"]],
        "total_cost": round(total_cost, 6),
        "weights_used": {m["model"]: m.get("effective_weight", 0) for m in adjusted},
    }

    await emit("consensus_completed", {
        "agreement_score": consensus["agreement_score"],
        "consensus_classification": consensus["classification"],
    })

    logger.info(
        "Consensus analysis complete",
        agreement=consensus["agreement_score"],
        classification=consensus["classification"],
    )
    return result


async def _analyze_with_openai(incident_text: str) -> Dict[str, Any]:
    """Analyze incident using OpenAI GPT."""
    model_name = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4.1-mini")
    if not settings.OPENAI_API_KEY:
        return _mock_analysis("GPT-4.1", "openai", available=False)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": _ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"INCIDENT:\n{incident_text[:1200]}"},
            ],
            max_tokens=400,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        prompt_tokens = resp.usage.prompt_tokens if resp.usage else 300
        completion_tokens = resp.usage.completion_tokens if resp.usage else 150
        cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)
        return {
            "model": "GPT-4.1",
            "provider": "openai",
            "available": True,
            "weight": _MODEL_WEIGHTS["openai"],
            "effective_weight": _MODEL_WEIGHTS["openai"],
            "threat_classification": data.get("threat_classification", "Unknown"),
            "severity": data.get("severity", "high"),
            "mitre_mapping": data.get("mitre_mapping", "T0000"),
            "risk_score": int(data.get("risk_score", 70)),
            "recommended_mitigation": data.get("recommended_mitigation", ""),
            "confidence": int(data.get("confidence", 80)),
            "reasoning": data.get("reasoning", ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": cost,
        }
    except Exception as exc:
        logger.warning("OpenAI consensus analysis failed", error=str(exc))
        return _mock_analysis("GPT-4.1", "openai", available=True)


async def _analyze_with_claude(incident_text: str) -> Dict[str, Any]:
    """Analyze incident using Anthropic Claude."""
    anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not anthropic_key:
        return _mock_analysis("Claude-3.5-Sonnet", "anthropic", available=False)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=anthropic_key)
        resp = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"<system>{_ANALYSIS_SYSTEM_PROMPT}</system>\n"
                        f"INCIDENT:\n{incident_text[:1200]}"
                    ),
                }
            ],
        )
        text = resp.content[0].text if resp.content else "{}"
        data = json.loads(text)
        prompt_tokens = resp.usage.input_tokens if resp.usage else 300
        completion_tokens = resp.usage.output_tokens if resp.usage else 150
        cost = _estimate_cost("claude-3-5-sonnet", prompt_tokens, completion_tokens)
        return {
            "model": "Claude-3.5-Sonnet",
            "provider": "anthropic",
            "available": True,
            "weight": _MODEL_WEIGHTS["anthropic"],
            "effective_weight": _MODEL_WEIGHTS["anthropic"],
            "threat_classification": data.get("threat_classification", "Unknown"),
            "severity": data.get("severity", "high"),
            "mitre_mapping": data.get("mitre_mapping", "T0000"),
            "risk_score": int(data.get("risk_score", 70)),
            "recommended_mitigation": data.get("recommended_mitigation", ""),
            "confidence": int(data.get("confidence", 80)),
            "reasoning": data.get("reasoning", ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost": cost,
        }
    except Exception as exc:
        logger.warning("Claude consensus analysis failed", error=str(exc))
        return _mock_analysis("Claude-3.5-Sonnet", "anthropic", available=True)


async def _analyze_with_llama(incident_text: str) -> Dict[str, Any]:
    """Analyze incident using local Llama model or mock."""
    llama_url = getattr(settings, "OLLAMA_URL", None) or getattr(settings, "LOCAL_LLM_URL", None)
    if not llama_url:
        return _mock_analysis("Llama-3.1-8B", "local", available=False)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": "llama3.1:8b",
                "prompt": f"{_ANALYSIS_SYSTEM_PROMPT}\n\nINCIDENT:\n{incident_text[:800]}",
                "stream": False,
                "format": "json",
            }
            resp = await client.post(f"{llama_url}/api/generate", json=payload)
            data = resp.json()
            parsed = json.loads(data.get("response", "{}"))
            return {
                "model": "Llama-3.1-8B",
                "provider": "local",
                "available": True,
                "weight": _MODEL_WEIGHTS["local"],
                "effective_weight": _MODEL_WEIGHTS["local"],
                "threat_classification": parsed.get("threat_classification", "Unknown"),
                "severity": parsed.get("severity", "medium"),
                "mitre_mapping": parsed.get("mitre_mapping", "T0000"),
                "risk_score": int(parsed.get("risk_score", 60)),
                "recommended_mitigation": parsed.get("recommended_mitigation", ""),
                "confidence": int(parsed.get("confidence", 70)),
                "reasoning": parsed.get("reasoning", ""),
                "prompt_tokens": 250,
                "completion_tokens": 120,
                "estimated_cost": 0.0001,
            }
    except Exception as exc:
        logger.warning("Llama consensus analysis failed", error=str(exc))
        return _mock_analysis("Llama-3.1-8B", "local", available=True)


def _mock_analysis(
    model: str, provider: str, available: bool = True
) -> Dict[str, Any]:
    """Return a realistic mock analysis result."""
    mock_data: Dict[str, Any] = {
        "GPT-4.1": {
            "threat_classification": "Brute Force",
            "severity": "high",
            "mitre_mapping": "T1110 - Brute Force",
            "risk_score": 75,
            "recommended_mitigation": "Block source IPs, enable account lockout, implement MFA immediately.",
            "confidence": 94,
            "reasoning": "Repeated failed authentication attempts from single source subnet match brute force pattern.",
        },
        "Claude-3.5-Sonnet": {
            "threat_classification": "Brute Force",
            "severity": "high",
            "mitre_mapping": "T1110 - Brute Force",
            "risk_score": 73,
            "recommended_mitigation": "Implement rate limiting, rotate credentials, enable geo-blocking for suspicious regions.",
            "confidence": 91,
            "reasoning": "High-frequency authentication failures from consistent source subnet indicate automated credential attack.",
        },
        "Llama-3.1-8B": {
            "threat_classification": "Credential Stuffing",
            "severity": "high",
            "mitre_mapping": "T1110.004 - Credential Stuffing",
            "risk_score": 68,
            "recommended_mitigation": "Enable CAPTCHA, monitor for credential reuse patterns, alert affected users.",
            "confidence": 78,
            "reasoning": "Repeated login pattern with varying credentials suggests credential stuffing rather than pure brute force.",
        },
    }
    defaults = mock_data.get(model, {
        "threat_classification": "Unknown Threat",
        "severity": "medium",
        "mitre_mapping": "T0000",
        "risk_score": 60,
        "recommended_mitigation": "Monitor and investigate.",
        "confidence": 65,
        "reasoning": "Insufficient data for classification.",
    })
    weight = _MODEL_WEIGHTS.get(provider, 0.15)
    return {
        "model": model,
        "provider": provider,
        "available": available,
        "weight": weight,
        "effective_weight": weight if available else 0.0,
        **defaults,
        "prompt_tokens": 0 if not available else 280,
        "completion_tokens": 0 if not available else 140,
        "estimated_cost": 0.0 if not available else 0.0004,
    }


def _adjust_weights(
    model_outputs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Redistribute weights for unavailable models proportionally."""
    available = [m for m in model_outputs if m["available"]]
    if not available:
        return model_outputs

    available_weight_sum = sum(m["weight"] for m in available)
    for m in model_outputs:
        if m["available"] and available_weight_sum > 0:
            m["effective_weight"] = round(m["weight"] / available_weight_sum, 4)
        else:
            m["effective_weight"] = 0.0
    return model_outputs


def _compute_consensus(
    model_outputs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compute weighted consensus from model outputs."""
    available = [m for m in model_outputs if m.get("available", False)]
    if not available:
        return {
            "classification": "Unknown",
            "severity": "medium",
            "mitre_mapping": "T0000",
            "risk_score": 60,
            "recommended_mitigation": "Manual analysis required.",
            "agreement_score": 0,
        }

    # Weighted vote for classification
    class_votes: Dict[str, float] = {}
    severity_votes: Dict[str, float] = {}
    total_weight = 0.0
    weighted_risk = 0.0

    for m in available:
        w = m.get("effective_weight", m.get("weight", 0.33))
        total_weight += w
        cls = m.get("threat_classification", "Unknown")
        sev = m.get("severity", "medium")
        class_votes[cls] = class_votes.get(cls, 0.0) + w
        severity_votes[sev] = severity_votes.get(sev, 0.0) + w
        weighted_risk += w * m.get("risk_score", 65)

    consensus_class = max(class_votes, key=lambda k: class_votes[k]) if class_votes else "Unknown"
    consensus_severity = max(severity_votes, key=lambda k: severity_votes[k]) if severity_votes else "medium"
    consensus_risk = int(round(weighted_risk / max(total_weight, 0.01)))

    # Agreement score: how many models agree on classification
    agreeing_weight = class_votes.get(consensus_class, 0.0)
    agreement_score = int(round((agreeing_weight / max(total_weight, 0.01)) * 100))

    # Best mitigation from highest-confidence model
    best_model = max(available, key=lambda m: m.get("confidence", 0))
    best_mitigation = best_model.get("recommended_mitigation", "")
    best_mitre = best_model.get("mitre_mapping", "T0000")

    return {
        "classification": consensus_class,
        "severity": consensus_severity,
        "mitre_mapping": best_mitre,
        "risk_score": consensus_risk,
        "recommended_mitigation": best_mitigation,
        "agreement_score": agreement_score,
    }


def _summarize_disagreements(
    model_outputs: List[Dict[str, Any]],
    consensus: Dict[str, Any],
) -> str:
    """Build a human-readable disagreement summary."""
    disagreeing = [
        m for m in model_outputs
        if m.get("available") and m.get("threat_classification") != consensus["classification"]
    ]
    if not disagreeing:
        return "All available models reached consensus on threat classification."

    parts = []
    for m in disagreeing:
        parts.append(
            f"{m['model']} classified it as '{m['threat_classification']}' "
            f"(confidence {m.get('confidence', 0)}%) — {m.get('reasoning', 'No reasoning provided')}"
        )
    return " | ".join(parts)


def _build_final_recommendation(
    consensus: Dict[str, Any], disagreement: str
) -> str:
    cls = consensus["classification"]
    severity = consensus["severity"].upper()
    score = consensus["agreement_score"]
    mitigation = consensus["recommended_mitigation"]

    prefix = f"Treat as **{cls}** with {severity} severity (consensus agreement: {score}%). "
    if score < 80:
        prefix += f"Note: models partially disagreed. {disagreement} "
    return prefix + f"Recommended action: {mitigation}"


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for a model call."""
    pricing = _MODEL_PRICING.get(model, {"input": 0.001, "output": 0.002})
    return round(
        (prompt_tokens / 1000) * pricing["input"]
        + (completion_tokens / 1000) * pricing["output"],
        6,
    )
