from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .common import MemoryStatus


class WALRecord(BaseModel):
    schema_version: int = 1
    skill_version: str = "1.0.0"

    wal_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    task_id: str
    item_type: str  # semantic | procedural | episodic
    payload: Dict[str, Any]
    payload_hash: str
    evidence_hashes: List[str] = Field(default_factory=list)
    status: MemoryStatus = MemoryStatus.PENDING
    store_result: Optional[str] = None  # record_id after commit


class WALStore(BaseModel):
    records: List[WALRecord] = Field(default_factory=list)
