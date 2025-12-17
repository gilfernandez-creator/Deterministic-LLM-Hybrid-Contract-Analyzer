# tests/test_normalize.py
from __future__ import annotations

from schemas import Deal
from graph.normalize import normalize_agent_outputs


def test_risk_classification_liability_high_month_1():
    deal = Deal(raw_text="dummy")
    state = {
        "deal": deal,
        "execution_trace": [],
        "risk_analysis": "- Limitation of liability is fees paid in the last 1 month",
        "raw_clause_extraction": "[]",
    }

    out = normalize_agent_outputs(state)
    items = out["risk_items"]

    assert any(r["category"] == "Liability" and r["severity"] == "High" for r in items), items
    assert out["risk_score"] > 0
