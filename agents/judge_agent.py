from __future__ import annotations

import json
import re
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import DealGraphState

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are the Judge / Synthesis Agent for a commercial deal risk system.

Hard rules:
- You may ONLY cite risks that appear in STRUCTURED_RISKS.
- Do NOT invent risks.
- Do not dramatize Low/Balanced risks; mention them only as context.
- Jurisdiction is NOT a risk unless marked Customer-Unfavorable or Medium/High.

Output MUST be valid JSON only (no markdown, no extra text) in this exact shape:
{{
  "rationale": "3-7 sentences, risks only",
  "key_risks": ["short phrase", "..."]  // 1-5 items, must be drawn from STRUCTURED_RISKS evidence
}}
"""),
    ("human", """
RISK SCORE (0-100): {risk_score}

STRUCTURED_RISKS:
{structured_risks}

TOP PRECEDENTS:
{precedents}

NEGOTIATION NOTES:
{negotiation_notes}
""")
])

def _format_structured_risks(risk_items: List[Dict[str, Any]]) -> str:
    if not risk_items:
        return "None"
    return "\n".join(
        f"- [{r.get('severity')}] {r.get('category')} ({r.get('direction')}): {r.get('evidence')}"
        for r in risk_items
    )

def _safe_json_loads(text: str) -> Dict[str, Any]:
    # strip ```json fences if they appear anyway
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)

def judge_agent(state: DealGraphState) -> Dict:
    trace = state.get("execution_trace", [])

    risk_items = state.get("risk_items", []) or []
    risk_score = float(state.get("risk_score", 0.0) or 0.0)
    precedents = state.get("supporting_precedents", []) or []
    negotiation_notes = state.get("negotiation_analysis") or "None"
    deal_text = getattr(state.get("deal"), "raw_text", "") or ""

    # Guardrail FIRST
    if len(deal_text) < 300 or not risk_items:
        return {
            "recommendation": "APPROVE_WITH_EDITS",
            "rationale": "Insufficient detail provided.",
            "confidence": 0.60,
            "execution_trace": trace + ["judge_agent"],
            "current_node": "judge",
        }

    structured_risks = _format_structured_risks(risk_items)
    precedents_text = "\n".join([f"- {p}" for p in precedents]) if precedents else "None"

    # Deterministic decision policy
    core_high = [
        r for r in risk_items
        if r.get("severity") == "High"
        and r.get("category") in ["Termination", "Liability", "Service Changes"]
    ]
    high_count = len(core_high)
    has_high_liability = any(r.get("severity") == "High" and r.get("category") == "Liability" for r in risk_items)
    has_high_termination = any(r.get("severity") == "High" and r.get("category") == "Termination" for r in risk_items)

    if risk_score >= 60 or high_count >= 2 or has_high_liability or has_high_termination:
        recommendation = "REJECT"
    elif risk_score >= 30 or high_count == 1:
        recommendation = "APPROVE_WITH_EDITS"
    else:
        recommendation = "APPROVE"

    confidence = 0.80 if recommendation != "REJECT" else 0.75

    resp = llm.invoke(JUDGE_PROMPT.format(
        risk_score=f"{risk_score:.1f}",
        structured_risks=structured_risks,
        precedents=precedents_text,
        negotiation_notes=negotiation_notes
    ))

    try:
        obj = _safe_json_loads(resp.content)
        rationale = (obj.get("rationale") or "").strip()
        if not rationale:
            rationale = "Rationale could not be generated reliably from the provided structured risks."
    except Exception:
        # last-resort fallback (should be rare)
        rationale = "Rationale could not be parsed as JSON. Treat this as a judge formatting failure."

    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "confidence": float(confidence),
        "execution_trace": trace + ["judge_agent"],
        "current_node": "judge",
    }
