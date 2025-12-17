from typing import List, Dict, Optional
from pydantic import BaseModel

class Clause(BaseModel):
    type: str
    text: str
    risk_level: Optional[str] = None

class DealState(BaseModel):
    deal_id: str
    raw_text: str
    clauses: List[Clause] = []
    risks: Dict[str, str] = {}
    precedents: List[str] = []
    recommendation: Optional[str] = None
