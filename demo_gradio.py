# demo_gradio.py
from __future__ import annotations

import os
import json
import gradio as gr

from graph.deal_graph import build_graph
from schemas import Deal


def format_risk_items(items: list[dict]) -> str:
    if not items:
        return "No risks extracted."

    lines = []
    for r in items:
        cat = r.get("category", "Other")
        sev = r.get("severity", "Medium")
        direction = r.get("direction", "Balanced")
        ev = r.get("evidence", "").strip()
        lines.append(f"- [{sev}] {cat} ({direction}): {ev}")
    return "\n".join(lines)


def run_dealgraph(deal_text: str) -> tuple[str, str, str, str]:
    deal_text = (deal_text or "").strip()
    if not deal_text:
        return "—", "0.0", "—", "Paste a contract excerpt to analyze."

    app = build_graph()
    state = {"deal": Deal(raw_text=deal_text), "execution_trace": []}
    out = app.invoke(state)

    rec = out.get("recommendation", "—")
    score = f"{float(out.get('risk_score', 0.0) or 0.0):.1f}"
    confidence = f"{float(out.get('confidence', 0.0) or 0.0):.2f}"

    risk_items = out.get("risk_items") or []
    rationale = out.get("rationale") or ""

    formatted = format_risk_items(risk_items)

    # Return:
    # 1) headline summary
    # 2) risk items markdown
    # 3) raw JSON for nerds/recruiters
    # 4) rationale
    headline = f"**Recommendation:** {rec}\n\n**Risk score:** {score}\n\n**Confidence:** {confidence}"
    raw_json = json.dumps(
        {
            "recommendation": rec,
            "risk_score": float(score),
            "confidence": float(confidence),
            "risk_vector": out.get("risk_vector", {}),
            "risk_items": risk_items,
            "supporting_precedents": out.get("supporting_precedents", []),
        },
        indent=2,
    )

    return headline, formatted, raw_json, rationale


EXAMPLE_1 = """Customer pays $5,000/month billed monthly. Term is 12 months.
Provider may change or discontinue features at any time without notice.
Customer may not terminate for convenience. Provider may terminate immediately for any breach.
Limitation of liability is fees paid in the last 1 month. No service credits for downtime.
Governing law: Delaware. Venue: Delaware."""

EXAMPLE_2 = """Subscription Term. The initial term is twelve (12) months.
Either party may terminate for convenience with thirty (30) days’ written notice.
Fees paid for unused months will be refunded on a prorated basis.
Customer shall pay $3,000 per month. Fees are fixed.
Provider guarantees 99.9% uptime measured monthly. Service credits apply for downtime.
Each party’s liability is capped at two (2) times the fees paid in the twelve (12) months preceding the claim.
Any changes must be mutually agreed in writing."""


with gr.Blocks(title="DealGraph — Deterministic LLM + Rules Contract Risk Analyzer") as demo:
    gr.Markdown(
        """
# DealGraph (Demo)
Hybrid pipeline:
- **LLM** extracts clause/risk signals
- **Deterministic normalizer** enforces consistent categories + scoring
- **LLM judge** produces a short rationale, while recommendation is policy-driven

> Requires `OPENAI_API_KEY` in your environment.
        """.strip()
    )

    with gr.Row():
        deal_text = gr.Textbox(
            label="Paste deal text",
            lines=14,
            placeholder="Paste contract excerpt here…",
            value=EXAMPLE_1,
        )

    with gr.Row():
        run_btn = gr.Button("Analyze", variant="primary")
        ex1_btn = gr.Button("Load Example (High Risk)")
        ex2_btn = gr.Button("Load Example (Balanced)")

    with gr.Row():
        headline = gr.Markdown(label="Summary")
    with gr.Row():
        risks_md = gr.Markdown(label="Structured risks")
    with gr.Row():
        rationale = gr.Textbox(label="Rationale", lines=6)
    with gr.Row():
        raw_json = gr.Code(label="Raw output JSON", language="json")

    run_btn.click(fn=run_dealgraph, inputs=[deal_text], outputs=[headline, risks_md, raw_json, rationale])
    ex1_btn.click(fn=lambda: EXAMPLE_1, inputs=[], outputs=[deal_text])
    ex2_btn.click(fn=lambda: EXAMPLE_2, inputs=[], outputs=[deal_text])

if __name__ == "__main__":
    # If OPENAI_API_KEY isn't set, Gradio will still open but calls will fail.
    demo.launch()
