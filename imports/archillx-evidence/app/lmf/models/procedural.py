from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProceduralItem(BaseModel):
    id: str
    name: str
    goal: str
    prerequisites: List[str] = Field(default_factory=list)
    steps: List[str] = Field(
        default_factory=list,
        description="List of steps or command templates",
    )
    safety_notes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(
        default_factory=list,
        description="References to episodic evidence",
    )
    dedupe_key: Optional[str] = None
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


class ProceduralStore(BaseModel):
    items: List[ProceduralItem] = Field(default_factory=list)
