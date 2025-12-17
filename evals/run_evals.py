# evals/run_evals.py
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from langsmith import expect

from graph.deal_graph import build_graph
from schemas import Deal


def load_cases(path: Path) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))
    return cases


def check_case(out: Dict[str, Any], expect: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    rec = out.get("recommendation")
    score = float(out.get("risk_score", 0.0) or 0.0)
    conf = float(out.get("confidence", 0.0) or 0.0)
    items = out.get("risk_items") or []
    cats = {r.get("category") for r in items if isinstance(r, dict)}
    # risk_vector exact or partial match
    expected_vec = expect.get("risk_vector")
    if isinstance(expected_vec, dict):
        got_vec = out.get("risk_vector") or {}
        for cat, sev in expected_vec.items():
            if got_vec.get(cat) != sev:
                errors.append(f"risk_vector[{cat}] expected {sev} got {got_vec.get(cat)}")

    # recommendation exact
    if "recommendation" in expect:
        if rec != expect["recommendation"]:
            errors.append(f"recommendation expected {expect['recommendation']} got {rec}")

    # recommendation one-of
    if "recommend" in expect and isinstance(expect["recommend"], dict):
        one_of = expect["recommend"].get("one_of")
        if one_of and rec not in one_of:
            errors.append(f"recommendation expected one_of={one_of} got {rec}")

    # risk score bounds
    if "min_risk_score" in expect and score < float(expect["min_risk_score"]):
        errors.append(f"risk_score expected >= {expect['min_risk_score']} got {score:.1f}")
    if "max_risk_score" in expect and score > float(expect["max_risk_score"]):
        errors.append(f"risk_score expected <= {expect['max_risk_score']} got {score:.1f}")

    # confidence bounds
    if "max_confidence" in expect and conf > float(expect["max_confidence"]):
        errors.append(f"confidence expected <= {expect['max_confidence']} got {conf:.2f}")

    # must-have categories
    must = expect.get("must_have_categories") or []
    missing = [c for c in must if c not in cats]
    if missing:
        errors.append(f"missing categories: {missing} (got {sorted(list(cats))})")

    return errors


def main() -> int:
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = load_cases(cases_path)

    app = build_graph()

    total = 0
    failed = 0

    for c in cases:
        total += 1
        deal_text = c["deal_text"]
        expect = c["expect"]

        state = {
            "deal": Deal(raw_text=deal_text),
            "execution_trace": [],
        }

        out = app.invoke(state)

        errs = check_case(out, expect)
        if errs:
            failed += 1
            print(f"\n❌ FAIL: {c['id']}")
            for e in errs:
                print(f"  - {e}")
            print(f"  got recommendation={out.get('recommendation')} risk_score={out.get('risk_score')} confidence={out.get('confidence')}")
        else:
            print(f"✅ PASS: {c['id']}  rec={out.get('recommendation')} score={float(out.get('risk_score',0)):.1f}")

    print(f"\n=== EVAL SUMMARY ===\npassed={total-failed}/{total}  failed={failed}/{total}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
