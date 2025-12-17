import uuid
import sys
from schemas import Deal
from graph.deal_graph import build_graph

from memory.snapshot import build_snapshot
from memory.deal_history import append_snapshot


def build_initial_state(deal_text: str):
    deal = Deal(deal_id=str(uuid.uuid4()), raw_text=deal_text)

    return {
        "deal": deal,

        # agent outputs (raw)
        "raw_clause_extraction": None,
        "clause_analysis": None,
        "risk_analysis": None,
        "precedent_analysis": None,
        "negotiation_analysis": None,

        # normalized/aggregated
        "extracted_risks": {},
        "risk_items": [],          # NEW: list of structured risk dicts
        "risk_score": 0.0,         # NEW: 0..100
        "risk_vector": {},     
        "supporting_precedents": [],

        # final decision
        "recommendation": None,
        "rationale": None,
        "confidence": None,

        # control/debug
        "current_node": "start",
        "execution_trace": [],
    }


if __name__ == "__main__":
    print("Paste deal text. Press Ctrl+Z then Enter when done:\n")
    deal_text = sys.stdin.read()
    print(f"\n--- DEBUG: got {len(deal_text)} chars ---")

    state = build_initial_state(deal_text)

    app = build_graph()
    print("Running DealGraph...")
    print("Graph finished.")
    final_state = app.invoke(state)
    print("\n--- RISK SCORE ---")
    print(final_state.get("risk_score"))

    print("\n--- RISK VECTOR ---")
    print(final_state.get("risk_vector"))

    print("\n--- RISK ITEMS ---")
    for r in final_state.get("risk_items", []):
        print("-", r)

    print("\n--- DEBUG: FINAL STATE KEYS ---")
    print(list(final_state.keys()))

    for k in ["clauses", "risks", "precedents", "negotiation", "recommendation", "rationale"]:
        if k in final_state:
            v = final_state[k]
            print(f"\n[{k}] type={type(v)} preview={str(v)[:200]}")

    # Save snapshot for precedent memory (so future runs retrieve history)
    append_snapshot(build_snapshot(final_state))

    print("\n--- EXECUTION TRACE ---")
    print(" -> ".join(final_state.get("execution_trace", [])))

    print("\n--- FINAL RECOMMENDATION ---")
    print(final_state.get("recommendation"))

    print("\n--- EXTRACTED RISKS (normalized) ---")
    for k, v in (final_state.get("extracted_risks") or {}).items():
        print(f"- {v}")

    print("\n--- RATIONALE ---")
    print(final_state.get("rationale"))

    print("\n--- TOP PRECEDENTS ---")
    for p in final_state.get("supporting_precedents", []):
        print("-", p)
