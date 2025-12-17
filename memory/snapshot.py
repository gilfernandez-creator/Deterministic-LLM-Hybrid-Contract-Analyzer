from typing import Dict, Any

def build_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    deal = state.get("deal")

    clauses = []
    for c in getattr(deal, "clauses", []) or []:
        clauses.append({"type": c.type, "text": c.text})

    # keep old for backwards compat
    risks = state.get("extracted_risks", {}) or {}

    # NEW structured outputs (Phase 2)
    risk_items = state.get("risk_items", []) or []
    risk_vector = state.get("risk_vector", {}) or {}
    risk_score = float(state.get("risk_score", 0.0) or 0.0)

    # summary should reflect structured risks first
    if risk_items:
        top = risk_items[:3]
        summary = " | ".join([r.get("evidence", "") for r in top if isinstance(r, dict)])
    else:
        summary = " | ".join(list(risks.values())[:3])

    if not summary:
        summary = "Low-risk or insufficient detail deal."

    return {
        "deal_id": getattr(deal, "deal_id", None),
        "clauses": clauses,
        "risks": risks,

        # NEW
        "risk_items": risk_items,
        "risk_vector": risk_vector,
        "risk_score": risk_score,

        "recommendation": state.get("recommendation"),
        "summary": summary[:300],
    }
