from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class LayerType(str, Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"


class ActionType(str, Enum):
    DISCARD = "DISCARD"
    COMPRESS = "COMPRESS"
    PERSIST = "PERSIST"


class EventType(str, Enum):
    TOOL_CALL = "TOOL_CALL"
    DECISION = "DECISION"
    CHECKPOINT = "CHECKPOINT"
    ERROR = "ERROR"
    USER_INPUT = "USER_INPUT"
    SYSTEM_OUTPUT = "SYSTEM_OUTPUT"
    TASK_COMPLETE = "TASK_COMPLETE"


class MemoryStatus(str, Enum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    DISCARDED = "DISCARDED"


class MemoryReport(BaseModel):
    schema_version: str = "1.0"
    skill_version: str = "1.0"

    task_id: str
    project: str
    created_at: datetime = Field(default_factory=datetime.now)

    events_total: int = 0
    tool_calls_total: int = 0
    errors_total: int = 0

    exec_core_task_ids: List[str] = Field(default_factory=list)

    persisted_semantic_count: int = 0
    persisted_procedural_count: int = 0

    committed_wal_ids: List[str] = Field(default_factory=list)
    semantic_record_ids: List[str] = Field(default_factory=list)
    procedural_record_ids: List[str] = Field(default_factory=list)
    evidence_hashes: List[str] = Field(default_factory=list)

    evidence_map: Dict[str, List[str]] = Field(default_factory=dict)

    status: str = "OK"
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)
