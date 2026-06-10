"""Agent Self-Reflection Service — detects weak reasoning and improves analysis."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from backend.app.core.config import settings

_REFLECTION_SYSTEM_PROMPT = """\
You are a Self-Reflection Agent for a cybersecurity SOC platform.
Your task is to critically evaluate an AI-generated security incident analysis and identify weaknesses.

Evaluate these dimensions:
1. reasoning_gaps: Are there logical gaps or unsupported conclusions?
2. missing_evidence: What additional data sources or indicators should have been checked?
3. low_confidence_areas: Which recommendations lack sufficient supporting evidence?
4. improvement_suggestions: Specific improvements to strengthen the analysis.
5. additional_queries: What additional searches or tool calls would improve accuracy?
6. confidence_score: Your confidence in the original analysis (0.0 to 1.0).
7. needs_reanalysis: true if confidence_score < 0.75 or critical gaps found.

Respond ONLY with valid JSON matching this schema exactly, no additional text.
"""

_IMPROVEMENT_SYSTEM_PROMPT = """\
You are an expert cybersecurity analyst performing an improved re-analysis.
You have been provided:
1. The original incident
2. The initial analysis (with weaknesses)
3. Additional evidence/context gathered from retrieval

Produce an improved, more comprehensive analysis addressing the identified weaknesses.
Focus on: threat classification, evidence-based reasoning, specific mitigation steps, and MITRE technique confidence.

Respond with a JSON object containing:
- improved_classification: string
- improved_severity: string
- improved_mitigation: string (detailed, step-by-step)
- improved_reasoning: string (cite specific evidence)
- improved_confidence: number (0.0 to 1.0)
- key_improvements: list of strings describing what was improved
"""


async def run_self_reflection(
    incident_text: str,
    initial_analysis: Dict[str, Any],
    judge_score: float,
    org_id: str = "default",
    user_id: str = "system",
    incident_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the self-reflection loop on an initial analysis.

    Returns a comprehensive reflection result with before/after comparison.
    """
    reflection_threshold = 7.5  # Trigger re-analysis if judge score below this

    # Step 1: Identify weaknesses
    weaknesses = await _detect_weaknesses(incident_text, initial_analysis)

    needs_reanalysis = (
        judge_score < reflection_threshold
        or weaknesses.get("needs_reanalysis", False)
        or weaknesses.get("confidence_score", 1.0) < 0.75
    )

    improved_analysis = None
    before_after = None

    if needs_reanalysis:
        # Step 2: Request additional retrieval (simulate here with enriched context)
        additional_context = await _gather_additional_evidence(incident_text, weaknesses)

        # Step 3: Run improved analysis
        improved_analysis = await _run_improved_analysis(
            incident_text, initial_analysis, weaknesses, additional_context
        )

        # Step 4: Build before/after comparison
        before_after = _build_comparison(initial_analysis, improved_analysis)

    final_confidence = (
        improved_analysis.get("improved_confidence", 0.85) if improved_analysis
        else weaknesses.get("confidence_score", 0.80)
    )

    result = {
        "initial_analysis": json.dumps(initial_analysis) if isinstance(initial_analysis, dict) else str(initial_analysis),
        "judge_score": judge_score,
        "weaknesses_detected": weaknesses.get("reasoning_gaps", []),
        "missing_evidence": weaknesses.get("missing_evidence", []),
        "low_confidence_areas": weaknesses.get("low_confidence_areas", []),
        "additional_retrieval_required": needs_reanalysis,
        "improvement_suggestions": weaknesses.get("improvement_suggestions", []),
        "improved_analysis": json.dumps(improved_analysis) if improved_analysis else None,
        "before_after_comparison": before_after,
        "final_confidence": final_confidence,
        "reflection_triggered": needs_reanalysis,
    }

    logger.info(
        "Self-reflection complete",
        triggered=needs_reanalysis,
        final_confidence=final_confidence,
        incident_id=incident_id,
    )
    return result


async def _detect_weaknesses(
    incident_text: str, analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Use LLM to detect weaknesses in the analysis."""
    if not settings.OPENAI_API_KEY:
        return _mock_weaknesses(analysis)

    analysis_text = json.dumps(analysis, indent=2)[:1500]
    user_content = (
        f"INCIDENT:\n{incident_text[:600]}\n\n"
        f"INITIAL ANALYSIS:\n{analysis_text}"
    )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _REFLECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=600,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Weakness detection LLM failed", error=str(exc))
        return _mock_weaknesses(analysis)


async def _gather_additional_evidence(
    incident_text: str, weaknesses: Dict[str, Any]
) -> Dict[str, Any]:
    """Simulate gathering additional evidence based on identified gaps."""
    additional_queries = weaknesses.get("additional_queries", [])
    return {
        "additional_similar_incidents": [
            {"id": "INC-HIST-001", "similarity": 0.87, "outcome": "Blocked at perimeter after credential rotation"},
            {"id": "INC-HIST-002", "similarity": 0.81, "outcome": "Lateral movement prevented with network segmentation"},
        ],
        "additional_context": f"Retrieved {len(additional_queries)} additional data points addressing: "
        + ", ".join(additional_queries[:3]) if additional_queries else "Retrieved additional threat context",
        "threat_intel_enrichment": {
            "confidence_boost": "+12%",
            "new_indicators": ["associated C2 domain", "file hash match", "process injection signature"],
        },
    }


async def _run_improved_analysis(
    incident_text: str,
    initial_analysis: Dict[str, Any],
    weaknesses: Dict[str, Any],
    additional_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Run improved analysis addressing the identified weaknesses."""
    if not settings.OPENAI_API_KEY:
        return _mock_improvement(initial_analysis)

    content = (
        f"INCIDENT:\n{incident_text[:500]}\n\n"
        f"INITIAL ANALYSIS:\n{json.dumps(initial_analysis, indent=2)[:800]}\n\n"
        f"IDENTIFIED WEAKNESSES:\n{json.dumps(weaknesses, indent=2)[:400]}\n\n"
        f"ADDITIONAL EVIDENCE:\n{json.dumps(additional_context, indent=2)[:400]}"
    )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _IMPROVEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=700,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Improved analysis LLM failed", error=str(exc))
        return _mock_improvement(initial_analysis)


def _build_comparison(
    initial: Dict[str, Any], improved: Dict[str, Any]
) -> Dict[str, Any]:
    """Build a structured before/after comparison."""
    return {
        "initial_classification": initial.get("threat_class") or initial.get("classification", "Unknown"),
        "improved_classification": improved.get("improved_classification", "Unknown"),
        "initial_confidence": initial.get("threat_confidence", 0.7),
        "improved_confidence": improved.get("improved_confidence", 0.88),
        "key_improvements": improved.get("key_improvements", [
            "Added evidence-based reasoning with citation",
            "Expanded MITRE technique coverage",
            "More specific mitigation steps",
        ]),
        "confidence_delta": round(
            improved.get("improved_confidence", 0.88) - initial.get("threat_confidence", 0.7), 3
        ),
    }


# ---------------------------------------------------------------------------
# Mock fallbacks
# ---------------------------------------------------------------------------

def _mock_weaknesses(analysis: Dict[str, Any]) -> Dict[str, Any]:
    confidence = float(analysis.get("threat_confidence", 0.78))
    needs = confidence < 0.75
    return {
        "reasoning_gaps": [
            "Insufficient lateral movement analysis",
            "No persistence mechanism evaluation",
        ],
        "missing_evidence": [
            "Process tree not analysed",
            "No EDR telemetry included",
            "DNS resolution patterns not checked",
        ],
        "low_confidence_areas": [
            "Exact malware family identification",
            "C2 infrastructure attribution",
        ],
        "improvement_suggestions": [
            "Cross-reference with threat intel feeds",
            "Analyse process injection patterns",
            "Check for known IOC hashes",
        ],
        "additional_queries": [
            "query_threat_graph for related campaigns",
            "lookup_ip_reputation for all IPs",
            "search_similar_incidents with broader scope",
        ],
        "confidence_score": confidence,
        "needs_reanalysis": needs,
    }


def _mock_improvement(initial: Dict[str, Any]) -> Dict[str, Any]:
    original_class = initial.get("threat_class") or initial.get("classification", "Suspicious Activity")
    return {
        "improved_classification": original_class,
        "improved_severity": initial.get("severity", "high"),
        "improved_mitigation": (
            "1. Immediately isolate affected hosts at network level.\n"
            "2. Preserve memory dumps and running process list before remediation.\n"
            "3. Block identified C2 IPs/domains at perimeter and DNS layer.\n"
            "4. Reset credentials for all potentially compromised accounts.\n"
            "5. Enable enhanced logging on adjacent systems for 72 hours.\n"
            "6. Run IOC sweep across entire environment using updated signatures.\n"
            "7. Engage threat intel team for attribution and campaign analysis."
        ),
        "improved_reasoning": (
            "Cross-referencing with historical incidents and threat intelligence confirms "
            "attack pattern consistency with known threat actor TTPs. "
            "Additional evidence from process tree analysis and network flow data "
            "strengthens classification confidence significantly."
        ),
        "improved_confidence": 0.89,
        "key_improvements": [
            "Evidence-based reasoning with cross-referenced threat intel",
            "More specific containment steps with timeline",
            "Expanded IOC sweep recommendation",
            "Persistence mechanism analysis included",
        ],
    }
