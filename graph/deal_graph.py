# graph/deal_graph.py
from langgraph.graph import StateGraph, END
from graph.state import DealGraphState

from agents.clause_agent import clause_agent
from agents.risk_agent import risk_agent
from graph.normalize import normalize_agent_outputs
from agents.precedent_agent import precedent_agent
from agents.negotiation_agent import negotiation_agent
from agents.judge_agent import judge_agent

def build_graph():
    graph = StateGraph(DealGraphState)

    graph.add_node("clauses", clause_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("normalize", normalize_agent_outputs)
    graph.add_node("precedent", precedent_agent)
    graph.add_node("negotiation", negotiation_agent)
    graph.add_node("judge", judge_agent)

    graph.set_entry_point("clauses")

    graph.add_edge("clauses", "risk")
    graph.add_edge("risk", "normalize")
    graph.add_edge("normalize", "precedent")
    graph.add_edge("precedent", "negotiation")
    graph.add_edge("negotiation", "judge")
    graph.add_edge("judge", END)

    return graph.compile()
