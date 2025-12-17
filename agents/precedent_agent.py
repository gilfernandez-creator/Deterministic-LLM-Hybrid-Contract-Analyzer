from __future__ import annotations
from typing import Dict, Any, List, Tuple

from graph.state import DealGraphState
from memory.deal_history import load_history
from memory.similarity import jaccard

TOP_K = 3

_SEV_ORDER = {"Low": 0, "Medium": 1, "High": 2}

def _sev_sim(a: str, b: str) -> float:
    if a not in _SEV_ORDER or b not in _SEV_ORDER:
        return 0.0
    da = abs(_SEV_ORDER[a] - _SEV_ORDER[b])
    if da == 0:
        return 1.0
    if da == 1:
        return 0.5
    return 0.0

def _risk_vector_similarity(v1: Dict[str, str], v2: Dict[str, str]) -> float:
    if not isinstance(v1, dict) or not isinstance(v2, dict) or not v1 or not v2:
        return 0.0
    cats = set(v1.keys()) | set(v2.keys())
    if not cats:
        return 0.0

    total = 0.0
    for c in cats:
        if c in v1 and c in v2:
            total += _sev_sim(v1[c], v2[c])
        else:
            total += 0.0
    return total / float(len(cats))

def _build_query_text(state: DealGraphState) -> str:
    deal = state["deal"]
    clause_text = "\n".join([c.text for c in getattr(deal, "clauses", [])]) or ""
    risks = state.get("extracted_risks", {})
    risk_text = "\n".join(risks.values()) if isinstance(risks, dict) else ""
    return f"CLAUSES:\n{clause_text}\n\nRISKS:\n{risk_text}".strip()

def _snapshot_to_text(s: Dict[str, Any]) -> str:
    clauses = s.get("clauses", [])
    risks = s.get("risks", {})
    clause_text = "\n".join([c.get("text","") for c in clauses if isinstance(c, dict)])
    risk_text = "\n".join(list(risks.values())) if isinstance(risks, dict) else ""
    return f"CLAUSES:\n{clause_text}\n\nRISKS:\n{risk_text}".strip()

def precedent_agent(state: DealGraphState) -> Dict:
    trace = state.get("execution_trace", [])
    history = load_history()

    # NEW: vector-first
    query_vec = state.get("risk_vector", {}) or {}

    scored: List[Tuple[float, Dict[str, Any]]] = []
    if query_vec:
        for item in history:
            cand_vec = item.get("risk_vector", {}) or {}
            score = _risk_vector_similarity(query_vec, cand_vec)
            if score > 0:
                scored.append((score, item))

    # Fallback to old text similarity if vectors unavailable or no matches
    if not scored:
        query = _build_query_text(state)
        for item in history:
            candidate = _snapshot_to_text(item)
            score = jaccard(query, candidate)
            if score > 0:
                scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:TOP_K]

    supporting_precedents: List[str] = []
    for score, item in top:
        deal_id = item.get("deal_id") or item.get("id") or "unknown"
        rec = item.get("recommendation") or "unknown"
        snippet = (item.get("summary") or "").strip()

        # add tiny “vector view” for explainability
        vec = item.get("risk_vector", {})
        vec_str = ""
        if isinstance(vec, dict) and vec:
            vec_str = " vec=" + ",".join([f"{k}:{v}" for k, v in vec.items()])

        if not snippet:
            risks = item.get("risks", {})
            if isinstance(risks, dict) and risks:
                snippet = next(iter(risks.values()))

        supporting_precedents.append(
            f"[{score:.2f}] deal={deal_id} rec={rec}{vec_str} :: {snippet}"
        )

    precedent_analysis = (
        "No close precedents found in deal history."
        if not supporting_precedents
        else "Top similar historical precedents:\n" + "\n".join(f"- {p}" for p in supporting_precedents)
    )

    return {
        "supporting_precedents": supporting_precedents,
        "precedent_analysis": precedent_analysis,
        "execution_trace": trace + ["precedent_agent"],
        "current_node": "precedent",
    }
