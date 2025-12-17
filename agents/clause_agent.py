from __future__ import annotations

from typing import Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from graph.state import DealGraphState

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

CLAUSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
You are a legal document parser.

Extract ONLY explicitly stated contractual clauses from the deal text.
- Do NOT infer missing terms
- Do NOT assess risk or fairness
- Output MUST be valid JSON ONLY (no markdown, no commentary)

Return a JSON array of objects.
Each object MUST have exactly two keys:
- "type": one of Payment, Termination, Liability, Indemnification, IP, Confidentiality, Security, Data Protection, Jurisdiction, Renewal, SLA, Other
- "text": the verbatim or near-verbatim clause text
"""),
    ("human", "DEAL TEXT:\n{deal_text}")
])

def clause_agent(state: DealGraphState) -> Dict:
    deal = state["deal"]
    trace = state.get("execution_trace", [])

    resp = llm.invoke(CLAUSE_PROMPT.format(deal_text=deal.raw_text))

    return {
        # raw output only; normalize will parse and update deal.clauses
        "raw_clause_extraction": resp.content,

        # optional: keep if you want; otherwise remove
        "clause_analysis": resp.content,

        "execution_trace": trace + ["clause_agent"],
        "current_node": "clauses",
    }
