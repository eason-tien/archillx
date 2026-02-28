from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class SelfHealingState(str, Enum):
    IDLE = "IDLE"
    DEGRADED = "DEGRADED"
    TAKEOVER = "TAKEOVER"
    REPAIRING = "REPAIRING"
    VERIFYING = "VERIFYING"
    HANDOFF_READY = "HANDOFF_READY"
    HANDOFF = "HANDOFF"
    COOLDOWN = "COOLDOWN"
    FAILED = "FAILED"


@dataclass
class SelfHealingEvent:
    phase: str
    action: str
    result: str
    detail: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
