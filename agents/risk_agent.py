# agents/risk_agent.py
from __future__ import annotations

import json
import re
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import DealGraphState

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

RISK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are a senior legal risk analyst specializing in commercial contracts.

Rules:
- Identify ONLY risks explicitly supported by the provided deal text / extracted clauses.
- Do NOT infer missing terms.
- Output MUST be valid JSON only (no markdown, no commentary).

Return this exact JSON shape:
{{
  "risks": [
    {{
      "category": "Payment|Termination|Liability|SLA|Service Changes|IP|Jurisdiction|Other",
      "risk": "short description",
      "evidence": "verbatim or near-verbatim snippet from the deal",
      "severity": "Low|Medium|High",
      "direction": "Customer-Favorable|Balanced|Customer-Unfavorable"
    }}
  ]
}}
"""),
    ("human", """
DEAL TEXT:
{deal_text}

EXTRACTED CLAUSES (if any):
{clauses}
""")
])

def _try_parse_risk_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and isinstance(obj.get("risks"), list):
            return obj
    except Exception:
        pass
    return {"risks": []}

def risk_agent(state: DealGraphState) -> Dict:
    deal = state["deal"]
    trace = state.get("execution_trace", [])

    clauses_text = (
        "\n".join([f"- {c.type}: {c.text}" for c in getattr(deal, "clauses", [])])
        if getattr(deal, "clauses", None) else "None"
    )

    resp = llm.invoke(RISK_PROMPT.format(
        deal_text=deal.raw_text,
        clauses=clauses_text
    ))

    # Store as JSON string (guaranteed parseable downstream)
    parsed = _try_parse_risk_json(resp.content)
    risk_analysis = json.dumps(parsed, ensure_ascii=False)

    return {
        "risk_analysis": risk_analysis,
        "execution_trace": trace + ["risk_agent"],
        "current_node": "risk",
    }
