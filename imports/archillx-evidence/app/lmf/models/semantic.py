from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SemanticItem(BaseModel):
    id: str
    title: str
    claim: str = Field(description="Reusable conclusion or claim")
    context: Optional[str] = Field(None, description="Scope or boundary of the claim")
    tags: List[str] = Field(default_factory=list)
    project: str
    confidence: float = Field(ge=0, le=1)
    evidence_refs: List[str] = Field(
        default_factory=list,
        description="References to episodic evidence",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    dedupe_key: Optional[str] = None
    superseded_by: Optional[str] = None


class SemanticStore(BaseModel):
    items: List[SemanticItem] = Field(default_factory=list)
