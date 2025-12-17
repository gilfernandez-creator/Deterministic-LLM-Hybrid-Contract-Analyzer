import json
import re
from typing import Dict, List, Any

from graph.state import DealGraphState
from schemas import Clause  # or from models.deal import Clause, depending on your layout


CATEGORIES = [
    "Payment",
    "Termination",
    "Liability",
    "SLA",
    "Service Changes",
    "IP",
    "Jurisdiction",
    "Other",
]

def _severity_points(sev: str) -> int:
    return {"Low": 1, "Medium": 3, "High": 6}.get(sev, 2)

def _classify_risk_line(line: str) -> Dict[str, Any]:
    """
    Deterministic classification of a single risk line into structured fields.
    """
    t = line.lower()

    # Category
    if any(k in t for k in ["terminate", "termination", "breach", "cure"]):
        category = "Termination"
    elif any(k in t for k in ["liability", "cap", "limit of liability", "damages"]):
        category = "Liability"
    elif any(k in t for k in ["uptime", "service credit", "sla"]):
        category = "SLA"
    elif any(k in t for k in ["change", "modify", "discontinue", "features"]):
        category = "Service Changes"
    elif any(k in t for k in ["fee", "payment", "invoice", "interest", "late"]):
        category = "Payment"
    elif any(k in t for k in ["ip", "intellectual property", "ownership", "license"]):
        category = "IP"
    elif any(k in t for k in ["governing law", "venue", "jurisdiction"]):
        category = "Jurisdiction"
    else:
        category = "Other"

    # Direction + Severity heuristics (customer perspective)
    direction = "Balanced"
    severity = "Medium"

    # Termination rules
    if category == "Termination":
        if "customer may not terminate" in t or "cannot terminate for convenience" in t:
            severity, direction = "High", "Customer-Unfavorable"
        elif ("provider can terminate immediately" in t) or ("provider may terminate immediately" in t) or ("provider may terminate" in t and "cure" not in t):
            severity, direction = "High", "Customer-Unfavorable"
        elif "30 days to cure" in t or "cure" in t:
            severity, direction = "Low", "Balanced"
        elif "terminate for convenience" in t and "customer" in t:
            severity, direction = "Low", "Customer-Favorable"

    # Liability rules
    if category == "Liability":
        m = re.search(r"last\s+(\d+)\s+month", t)
        if m:
            months = int(m.group(1))
            if months <= 1:
                severity, direction = "High", "Customer-Unfavorable"
            elif months <= 3:
                severity, direction = "Medium", "Customer-Unfavorable"
            else:
                severity, direction = "Low", "Balanced"
        else:
            # Any liability cap mention without detail is at least medium
            severity, direction = "Medium", "Balanced"

    # SLA rules
    if category == "SLA":
        if "no service credits" in t:
            severity, direction = "Medium", "Customer-Unfavorable"
        elif "service credits apply" in t:
            severity, direction = "Low", "Customer-Favorable"

    # Service changes rules
    if category == "Service Changes":
        # if approval is required, it's not "change at will"
        if ("approval" in t) or ("prior written approval" in t) or ("only with" in t and "approval" in t):
            # still allow security patches without approval = balanced
            if "security patch" in t or "security patches" in t:
                severity, direction = "Low", "Balanced"
            else:
                severity, direction = "Low", "Customer-Favorable"
        else:
            if "without notice" in t or "may change" in t or "discontinue" in t:
                severity, direction = "High", "Customer-Unfavorable"

    # Jurisdiction rules (don’t treat Delaware as scary by default)
    if category == "Jurisdiction":
        severity, direction = "Low", "Balanced"

    return {
        "category": category,
        "severity": severity,
        "direction": direction,
        "evidence": line.strip(),
    }

ALLOWED_CLAUSE_TYPES = {
    "Payment",
    "Termination",
    "Liability",
    "Indemnification",
    "IP",
    "Confidentiality",
    "Security",
    "Data Protection",
    "Jurisdiction",
    "Renewal",
    "SLA",
    "Other",
}


def _safe_json_loads(text: str) -> Any:
    """
    Tries to parse JSON even if the model wraps it in code fences.
    Returns None if parsing fails.
    """
    if not text:
        return None

    cleaned = text.strip()

    # Remove ```json fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        return None


def _normalize_clause_type(t: str) -> str:
    if not t:
        return "Other"
    t = t.strip()

    # Simple normalization heuristics
    mapping = {
        "governing law": "Jurisdiction",
        "law": "Jurisdiction",
        "venue": "Jurisdiction",
        "data": "Data Protection",
        "privacy": "Data Protection",
        "security": "Security",
        "termination": "Termination",
        "renewal": "Renewal",
        "indemnity": "Indemnification",
        "indemnification": "Indemnification",
        "liability": "Liability",
        "payment": "Payment",
        "fees": "Payment",
        "ip": "IP",
        "intellectual property": "IP",
        "confidentiality": "Confidentiality",
        "nda": "Confidentiality",
        "sla": "SLA",
        "service level": "SLA",
    }

    key = t.lower()
    if key in mapping:
        return mapping[key]

    # If the model returned something already close, keep it if allowed
    for allowed in ALLOWED_CLAUSE_TYPES:
        if allowed.lower() == key:
            return allowed

    return "Other"

def _parse_risk_analysis(risk_analysis: str) -> List[Dict[str, Any]]:
    """
    Accepts either:
    1) JSON string in the {"risks":[...]} shape, OR
    2) legacy bullet text.
    Returns a list of risk dicts.
    """
    if not risk_analysis:
        return []

    # Try JSON first
    parsed = _safe_json_loads(risk_analysis)
    if isinstance(parsed, dict) and isinstance(parsed.get("risks"), list):
        out = []
        for r in parsed["risks"]:
            if isinstance(r, dict):
                out.append(r)
        return out

    # Fallback: legacy bullet text -> convert to minimal dicts
    items = []
    for line in risk_analysis.splitlines():
        line = line.strip("-• \t").strip()
        if not line:
            continue
        items.append({
            "category": "Other",
            "risk": line,
            "evidence": line,
            "severity": "Medium",
            "direction": "Balanced",
        })
    return items

def normalize_agent_outputs(state: DealGraphState) -> Dict:
    """
    Deterministic LangGraph node.
    Parses/normalizes raw agent outputs into structured state.
    """

    deal = state["deal"]
    trace = state.get("execution_trace", [])

    # -------------------------
    # 1) Normalize Clauses
    # -------------------------
    raw = state.get("raw_clause_extraction") or state.get("clause_analysis") or "[]"

    parsed = _safe_json_loads(raw)

    normalized_clauses: List[Clause] = []

    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            clause_type = _normalize_clause_type(str(item.get("type", "")))
            clause_text = str(item.get("text", "")).strip()
            if not clause_text:
                continue
            normalized_clauses.append(Clause(type=clause_type, text=clause_text))

    # Update the domain object (deal.clauses) — this is the “stateful” part
    deal.clauses = normalized_clauses

    # -------------------------
# 2) Normalize Risks -> risk_items + risk_vector + risk_score
# -------------------------
        # -------------------------
    # 2) Normalize Risks (JSON-first)
    # -------------------------
    risk_raw = state.get("risk_analysis") or ""
    risk_list = _parse_risk_analysis(risk_raw)

    extracted_risks: Dict[str, str] = {}
    risk_items: List[Dict[str, Any]] = []

    for r in risk_list:
        risk_text = str(r.get("risk", "")).strip()
        evidence = str(r.get("evidence", "")).strip() or risk_text
        if not risk_text and not evidence:
            continue

        # backward-compatible extracted_risks
        key = " ".join((risk_text or evidence).split()[:6]).strip()
        if key and key not in extracted_risks:
            extracted_risks[key] = (risk_text or evidence)

        # ✅ deterministic overwrite (don’t trust LLM severity)
        det = _classify_risk_line(evidence or risk_text)
        risk_items.append({
            "category": det["category"],
            "severity": det["severity"],
            "direction": det["direction"],
            "evidence": det["evidence"],
            # optional: keep LLM output for audit/debug
            "llm_category": r.get("category"),
            "llm_severity": r.get("severity"),
            "llm_direction": r.get("direction"),
            "llm_risk": risk_text,
    })


    # risk_vector: category -> highest severity seen
    rank = {"Low": 1, "Medium": 2, "High": 3}
    risk_vector: Dict[str, str] = {}
    for r in risk_items:
        cat = r["category"]
        sev = r["severity"]
        if cat not in risk_vector or rank[sev] > rank[risk_vector[cat]]:
            risk_vector[cat] = sev
    # risk_score: 0..100 (simple additive v1)
    score = 0
    for cat, sev in risk_vector.items():
        score += _severity_points(sev)  # scale for demo
    # scale to 0..100 in a predictable way (max categories ~7)
    # max per category is 6 points; 7 categories => 42 points
    risk_score = min(100.0, (score / 42.0) * 100.0)
    risk_score = round(float(risk_score), 1)
    return {
    "deal": deal,
    "extracted_risks": extracted_risks,
    "risk_items": risk_items,
    "risk_vector": risk_vector,
    "risk_score": risk_score,
    "current_node": "normalize",
    "execution_trace": trace + ["normalize"],
}
