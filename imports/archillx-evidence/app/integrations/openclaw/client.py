"""
ArcHillx — OpenClaw Integration Client
Connects ArcHillx skills to an OpenClaw gateway for distributed skill invocation.
Gate: settings.enable_openclaw_integration
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from ...config import settings

logger = logging.getLogger(__name__)


class OpenClawClient:
    """
    Lightweight HTTP client for the OpenClaw gateway.
    Sends DispatchContract-compatible skill invocations to OpenClaw's
    /oc/tools/invoke endpoint and translates results back to ArcHillx format.
    """

    def __init__(self) -> None:
        self._base = settings.openclaw_base_url.rstrip("/")
        self._api_key = settings.openclaw_api_key
        self._timeout = 30.0

    @property
    def enabled(self) -> bool:
        return settings.enable_openclaw_integration and bool(self._base)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
        return h

    # ── Public API ────────────────────────────────────────────────────────────

    def invoke_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a remote skill through the OpenClaw gateway.
        Returns {"ok": bool, "result": Any, "error": str|None}
        """
        if not self.enabled:
            return {"ok": False, "result": None, "error": "OpenClaw integration disabled"}

        payload = {
            "skill": skill_name,
            "input": input_data,
            "task_id": task_id or "",
            "session_id": session_id or "",
            "source": "archillx",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base}/oc/tools/invoke",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return {"ok": True, "result": data.get("result"), "error": None}
        except httpx.HTTPStatusError as e:
            logger.warning("OpenClaw invoke HTTP error %s: %s", e.response.status_code, e)
            return {"ok": False, "result": None, "error": str(e)}
        except Exception as e:
            logger.warning("OpenClaw invoke error: %s", e)
            return {"ok": False, "result": None, "error": str(e)}

    def list_skills(self) -> List[Dict[str, Any]]:
        """Fetch the list of skills registered in the OpenClaw gateway."""
        if not self.enabled:
            return []
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(
                    f"{self._base}/oc/tools",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json().get("tools", [])
        except Exception as e:
            logger.warning("OpenClaw list_skills error: %s", e)
            return []

    def health(self) -> Dict[str, Any]:
        """Check OpenClaw gateway health."""
        if not self.enabled:
            return {"status": "disabled"}
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base}/health", headers=self._headers())
                resp.raise_for_status()
                return {"status": "ok", **resp.json()}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# Lazy singleton
_client: Optional[OpenClawClient] = None


def get_openclaw_client() -> OpenClawClient:
    global _client
    if _client is None:
        _client = OpenClawClient()
    return _client
