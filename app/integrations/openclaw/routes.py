"""
ArcHillx — OpenClaw Integration API Routes
Exposes /v1/integrations/openclaw/* endpoints when integration is enabled.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...config import settings
from .client import get_openclaw_client

router = APIRouter(prefix="/v1/integrations/openclaw", tags=["openclaw"])


class InvokeRequest(BaseModel):
    skill: str
    input: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    session_id: Optional[str] = None


def _check_enabled() -> None:
    if not settings.enable_openclaw_integration:
        raise HTTPException(status_code=503, detail="OpenClaw integration is disabled. Set ENABLE_OPENCLAW_INTEGRATION=true")


@router.get("/health")
def openclaw_health():
    _check_enabled()
    return get_openclaw_client().health()


@router.get("/skills")
def openclaw_list_skills():
    _check_enabled()
    return {"skills": get_openclaw_client().list_skills()}


@router.post("/invoke")
def openclaw_invoke(req: InvokeRequest):
    _check_enabled()
    result = get_openclaw_client().invoke_skill(
        skill_name=req.skill,
        input_data=req.input,
        task_id=req.task_id,
        session_id=req.session_id,
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "OpenClaw error"))
    return result
