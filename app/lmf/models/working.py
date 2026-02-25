from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WorkingMemory(BaseModel):
    task_id: Optional[str] = None
    goal: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
    facts_confirmed: List[str] = Field(default_factory=list)
