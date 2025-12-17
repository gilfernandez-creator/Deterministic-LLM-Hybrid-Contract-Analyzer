from typing import TypedDict, List, Dict, Optional, Any
from schemas import Deal



class DealGraphState(TypedDict):
    # ---- Domain Payload ----
    deal: Deal

    # ---- Agent Outputs ----
    clause_analysis: Optional[str]
    risk_analysis: Optional[str]
    raw_clause_extraction: Optional[str]
    precedent_analysis: Optional[str]
    negotiation_analysis: Optional[str]

    # ---- Aggregation ----
    extracted_risks: Dict[str, str]
    risk_items: List[Dict[str, Any]]     # NEW
    risk_vector: Dict[str, str]          # NEW
    risk_score: float     
    supporting_precedents: List[str]

    # ---- Final Decision ----
    recommendation: Optional[str]
    rationale: Optional[str]
    confidence: Optional[float]

    # ---- Graph Control ----
    current_node: str
    execution_trace: List[str]
