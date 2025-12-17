from __future__ import annotations

from typing import Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import DealGraphState

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

NEGOTIATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are a negotiation strategy analyst for commercial contracts.

Goal:
- Suggest the most important clauses to renegotiate based on provided risks and precedents.
- Provide concrete edits or negotiation positions.
- Define walk-away thresholds when risks are unacceptable.

Constraints:
- Do NOT restate the entire contract.
- Be concise and actionable.
- Output as a numbered list.
- Each item must include: (1) issue, (2) ask / redline idea, (3) rationale, (4) fallback if rejected.
"""),
    ("human", """
EXTRACTED RISKS (normalized):
{risks}

SUPPORTING PRECEDENTS:
{precedents}

DEAL CLAUSES (if available):
{clauses}
""")
])

def negotiation_agent(state: DealGraphState) -> Dict:
    trace = state.get("execution_trace", [])
    deal = state["deal"]

    risks = state.get("extracted_risks", {})          # ✅ normalized dict
    precedents = state.get("supporting_precedents", [])

    risks_text = (
        "\n".join([f"- {k}: {v}" for k, v in risks.items()])
        if isinstance(risks, dict) and risks
        else "None"
    )
    precedents_text = "\n".join([f"- {p}" for p in precedents]) if precedents else "None"
    clauses_text = (
        "\n".join([f"- {c.type}: {c.text}" for c in getattr(deal, "clauses", [])])
        if getattr(deal, "clauses", None) else "None"
    )

    resp = llm.invoke(NEGOTIATION_PROMPT.format(
        risks=risks_text,
        precedents=precedents_text,
        clauses=clauses_text
    ))

    return {
        "negotiation_analysis": resp.content,
        "execution_trace": trace + ["negotiation_agent"],
        "current_node": "negotiation",
    }

