from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class Clause(BaseModel):
    type: str
    text: str

class Deal(BaseModel):
    deal_id: Optional[str] = None
    raw_text: str
    clauses: List[Clause] = Field(default_factory=list)

class DealState(BaseModel):
    """
    If you ever choose to use Pydantic as the LangGraph state object,
    this must allow extra keys because agents will add fields over time.
    """
    model_config = ConfigDict(extra="allow")
