"""
ArcHillx — TRAE-Solo Integration
================================
Bridges ArcHillx with the TRAE-Solo coding agent:
  - POST /v1/integrations/trae/run      → submit a coding task
  - GET  /v1/integrations/trae/status   → check task status
  - GET  /v1/integrations/trae/health   → gateway health
  - GET  /v1/integrations/trae/models   → list available models

Gate: settings.enable_trae_solo_integration
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from ...config import settings

logger = logging.getLogger(__name__)


# ── TRAE-Solo client ──────────────────────────────────────────────────────────

class TraeSoloClient:
    """
    HTTP client for the TRAE-Solo coding agent gateway.
    TRAE-Solo is a multi-model agentic coding system; ArcHillx delegates
    code-generation tasks to it and polls for results.
    """

    def __init__(self) -> None:
        self._base = settings.trae_solo_base_url.rstrip("/")
        self._api_key = settings.trae_solo_api_key
        self._timeout = 60.0

    @property
    def enabled(self) -> bool:
        return settings.enable_trae_solo_integration and bool(self._base)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
        return h

    # ── Public API ────────────────────────────────────────────────────────────

    def run_task(
        self,
        prompt: str,
        *,
        language: Optional[str] = None,
        model: Optional[str] = None,
        context_files: Optional[List[Dict[str, str]]] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Submit a coding task to TRAE-Solo.

        Returns:
          {
            "ok": bool,
            "trae_task_id": str | None,
            "status": str,       # queued | running | completed | failed
            "result": Any,
            "error": str | None,
          }
        """
        if not self.enabled:
            return {
                "ok": False,
                "trae_task_id": None,
                "status": "disabled",
                "result": None,
                "error": "TRAE-Solo integration disabled",
            }

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "source": "archillx",
            "max_iterations": max_iterations,
        }
        if language:
            payload["language"] = language
        if model:
            payload["model"] = model
        if context_files:
            payload["context_files"] = context_files
        if task_id:
            payload["task_id"] = task_id
        if session_id:
            payload["session_id"] = session_id

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base}/trae/run",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "ok": True,
                    "trae_task_id": data.get("task_id"),
                    "status": data.get("status", "queued"),
                    "result": data.get("result"),
                    "error": None,
                }
        except httpx.HTTPStatusError as e:
            logger.warning("TRAE-Solo run HTTP error %s: %s", e.response.status_code, e)
            return {
                "ok": False,
                "trae_task_id": None,
                "status": "error",
                "result": None,
                "error": str(e),
            }
        except Exception as e:
            logger.warning("TRAE-Solo run error: %s", e)
            return {
                "ok": False,
                "trae_task_id": None,
                "status": "error",
                "result": None,
                "error": str(e),
            }

    def get_status(self, trae_task_id: str) -> Dict[str, Any]:
        """
        Poll the status of a submitted TRAE-Solo task.

        Returns:
          {
            "ok": bool,
            "trae_task_id": str,
            "status": str,    # queued | running | completed | failed
            "result": Any,
            "error": str | None,
          }
        """
        if not self.enabled:
            return {
                "ok": False,
                "trae_task_id": trae_task_id,
                "status": "disabled",
                "result": None,
                "error": "TRAE-Solo integration disabled",
            }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self._base}/trae/tasks/{trae_task_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "ok": True,
                    "trae_task_id": trae_task_id,
                    "status": data.get("status", "unknown"),
                    "result": data.get("result"),
                    "error": data.get("error"),
                }
        except httpx.HTTPStatusError as e:
            logger.warning("TRAE-Solo status HTTP error %s: %s", e.response.status_code, e)
            return {
                "ok": False,
                "trae_task_id": trae_task_id,
                "status": "error",
                "result": None,
                "error": str(e),
            }
        except Exception as e:
            logger.warning("TRAE-Solo status error: %s", e)
            return {
                "ok": False,
                "trae_task_id": trae_task_id,
                "status": "error",
                "result": None,
                "error": str(e),
            }

    def list_models(self) -> List[Dict[str, Any]]:
        """List models available in the TRAE-Solo gateway."""
        if not self.enabled:
            return []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self._base}/trae/models",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception as e:
            logger.warning("TRAE-Solo list_models error: %s", e)
            return []

    def health(self) -> Dict[str, Any]:
        """Check TRAE-Solo gateway health."""
        if not self.enabled:
            return {"status": "disabled"}
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{self._base}/health",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return {"status": "ok", **resp.json()}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# Lazy singleton
_client: Optional[TraeSoloClient] = None


def get_trae_client() -> TraeSoloClient:
    global _client
    if _client is None:
        _client = TraeSoloClient()
    return _client


# ── FastAPI Router ────────────────────────────────────────────────────────────

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v1/integrations/trae", tags=["trae-solo"])


class TraeRunRequest(BaseModel):
    prompt: str
    language: Optional[str] = None
    model: Optional[str] = None
    context_files: Optional[List[Dict[str, str]]] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    max_iterations: int = 10


def _check_enabled() -> None:
    if not settings.enable_trae_solo_integration:
        raise HTTPException(
            status_code=503,
            detail="TRAE-Solo integration is disabled. Set ENABLE_TRAE_SOLO_INTEGRATION=true",
        )


@router.get("/health")
def trae_health():
    _check_enabled()
    return get_trae_client().health()


@router.get("/models")
def trae_list_models():
    _check_enabled()
    return {"models": get_trae_client().list_models()}


@router.post("/run")
def trae_run(req: TraeRunRequest):
    _check_enabled()
    result = get_trae_client().run_task(
        prompt=req.prompt,
        language=req.language,
        model=req.model,
        context_files=req.context_files,
        task_id=req.task_id,
        session_id=req.session_id,
        max_iterations=req.max_iterations,
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "TRAE-Solo error"))
    return result


@router.get("/status/{trae_task_id}")
def trae_status(trae_task_id: str):
    _check_enabled()
    return get_trae_client().get_status(trae_task_id)
