from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .common import EventType, MemoryStatus


class EpisodicEvent(BaseModel):
    id: str = Field(description="Unique ID of the event")
    task_id: str
    seq: int
    event_type: EventType
    payload: Dict[str, Any] = Field(description="Summary or content of the event")
    stdout_sha256: Optional[str] = None
    stderr_sha256: Optional[str] = None
    payload_sha256: Optional[str] = None
    status: MemoryStatus = MemoryStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.now)
    evidence_hashes: List[str] = Field(default_factory=list)


class EpisodicStore(BaseModel):
    events: List[EpisodicEvent] = Field(default_factory=list)
