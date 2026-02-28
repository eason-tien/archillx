"""
ArcHillx — Remediation Planner
==============================
LLM-powered remediation advisor with full provenance logging.

Priority:
  1. If ArcHillx model router is available and responds → use LLM plan
     (provenance dict attached to plan for incident replay/audit)
  2. Otherwise → rule-based plan (no provenance)

Feature flag: settings.enable_autonomous_remediation
LLM calls go through ArcHillx model router (app.utils.model_router).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..config import settings

_ACTION_RISK_MAP: Dict[str, str] = {
    "config":             "LOW",
    "retry":              "LOW",
    "retry_with_backoff": "LOW",
    "fallback":           "MEDIUM",
    "alternative":        "MEDIUM",
    "restart":            "HIGH",
    "rollback":           "HIGH",
}

_LANG_INSTRUCTION: Dict[str, str] = {
    "zh-CN": "请用简体中文回答，步骤简洁清晰。",
    "zh-TW": "請用繁體中文回答，步驟簡潔清晰。",
    "en":    "Answer in English. Keep steps concise and actionable.",
}

_DEFAULT_LANG = "en"


# ── Provenance helpers ─────────────────────────────────────────────────────

def _sha256_prefix(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:n]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── RemediationPlan ────────────────────────────────────────────────────────

class RemediationPlan:
    def __init__(
        self,
        steps: List[Dict],
        risk_level: str,
        verification_strategy: Dict,
        source: str = "rule_based",
        summary: str = "",
        provenance: Optional[Dict] = None,
    ):
        self.plan_id               = str(uuid.uuid4())
        self.steps                 = steps
        self.risk_level            = risk_level
        self.verification_strategy = verification_strategy
        self.status                = "PLANNED"
        self.source                = source   # "llm" | "rule_based"
        self.summary               = summary
        self.provenance            = provenance or {}

    def to_dict(self) -> dict:
        return {
            "plan_id":               self.plan_id,
            "steps":                 self.steps,
            "risk_level":            self.risk_level,
            "verification_strategy": self.verification_strategy,
            "status":                self.status,
            "source":                self.source,
            "summary":               self.summary,
            "provenance":            self.provenance,
        }


# ── Prompt builder ─────────────────────────────────────────────────────────

def _build_prompt(
    action_signature: Dict[str, Any],
    matched_pattern:  Dict[str, Any],
    drift_status:     str,
    recent_errors:    List[str],
    lang:             str,
) -> str:
    lang_inst  = _LANG_INSTRUCTION.get(lang, _LANG_INSTRUCTION["en"])
    recent_str = "\n".join(f"  - {e}" for e in recent_errors[:5]) or "  (none)"

    return (
        f"{lang_inst}\n\n"
        "You are an expert autonomous remediation advisor for the ArcHillx system.\n"
        "Given the following context, produce a JSON remediation plan.\n\n"
        f"## Triggered Action\n{json.dumps(action_signature, ensure_ascii=False, indent=2)}\n\n"
        f"## Matched Error Pattern\n{json.dumps(matched_pattern, ensure_ascii=False, indent=2)}\n\n"
        f"## System Drift Status\n{drift_status}\n\n"
        f"## Recent Errors (last 5)\n{recent_str}\n\n"
        "## Output Format\n"
        "Return ONLY a JSON object (no markdown fences) with this structure:\n"
        '{"summary":"<one-sentence>","risk_level":"<LOW|MEDIUM|HIGH>",'
        '"steps":[{"step_id":1,"action":{"type":"<type>","params":{}},'
        '"description":"<what>","rationale":"<why>"}],'
        '"verification":{"type":"<execution_result|metric_check|manual_confirm>",'
        '"criteria":"<success condition>"}}\n'
        "Limit to 3-5 steps. If no safe remediation exists, return steps=[]."
    )


# ── Async LLM call via ArcHillx model router ────────────────────────────────

async def _call_router_async(
    prompt: str,
) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Call ArcHillx model router asynchronously.
    Returns (parsed_plan_dict, provenance_dict) or (None, None).
    """
    try:
        from ..utils.model_router import model_router
    except Exception:
        return None, None

    prompt_hash = _sha256_prefix(prompt)
    called_at   = _utcnow_iso()

    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: model_router.complete(
                prompt=prompt,
                task_type="remediation",
                budget="medium",
            ),
        )
    except Exception:
        return None, None

    raw = resp.content.strip()

    # Strip ```json ... ``` fences if present
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

    response_hash = _sha256_prefix(raw)

    try:
        parsed = json.loads(raw)
    except Exception:
        return None, None

    provenance: Dict[str, Any] = {
        "provider":      resp.provider,
        "model":         resp.model,
        "prompt_hash":   prompt_hash,
        "response_hash": response_hash,
        "called_at":     called_at,
    }
    return parsed, provenance


def _call_router_sync(
    prompt: str,
) -> Tuple[Optional[dict], Optional[dict]]:
    """Synchronous wrapper for the async router call."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(asyncio.run, _call_router_async(prompt))
            return fut.result(timeout=30)
    except Exception:
        return None, None


# ── Rule-based fallback ────────────────────────────────────────────────────

def _rule_based_plan(
    action_signature: Dict[str, Any],
    matched_pattern:  Dict[str, Any],
) -> Optional[RemediationPlan]:
    actions = matched_pattern.get("recommended_actions", [])
    if not actions:
        return None

    best_action = actions[0]
    atype       = best_action.get("type", "unknown")
    risk_level  = _ACTION_RISK_MAP.get(atype, "HIGH")

    steps = [{
        "step_id":     1,
        "action":      best_action,
        "description": f"Apply {atype} mitigation",
        "rationale":   "Highest-ranked action from matched causal pattern",
    }]

    return RemediationPlan(
        steps=steps,
        risk_level=risk_level,
        verification_strategy={"type": "execution_result", "criteria": "success_status"},
        source="rule_based",
        summary=(
            f"Rule-based {atype} remediation for "
            f"{matched_pattern.get('pattern_name', 'unknown')}"
        ),
        provenance={},
    )


# ── Main planner ───────────────────────────────────────────────────────────

class RemediationPlanner:
    """
    LLM-powered remediation advisor with full provenance logging.

    Gated by settings.enable_autonomous_remediation.
    Uses ArcHillx model router for LLM calls; falls back to rule-based logic.
    """

    def __init__(self, store: Any = None, lang: Optional[str] = None):
        self.store = store
        self.lang  = lang or _DEFAULT_LANG

    def create_plan(
        self,
        action_signature: Dict[str, Any],
        matched_pattern:  Dict[str, Any],
        drift_status:     str,
        recent_errors:    Optional[List[str]] = None,
    ) -> Optional[RemediationPlan]:
        """
        Generate a remediation plan.
        Returns None if feature flag is disabled or no pattern matched.
        """
        if not getattr(settings, "enable_autonomous_remediation", False):
            return None

        if not matched_pattern:
            return None

        recent_errors = recent_errors or []

        # ── LLM path ──────────────────────────────────────────────────────
        try:
            prompt = _build_prompt(
                action_signature, matched_pattern,
                drift_status, recent_errors, self.lang,
            )
            llm_out, provenance = _call_router_sync(prompt)

            if llm_out and llm_out.get("steps"):
                return RemediationPlan(
                    steps=llm_out["steps"],
                    risk_level=llm_out.get("risk_level", "MEDIUM"),
                    verification_strategy=llm_out.get("verification", {
                        "type": "execution_result",
                        "criteria": "success_status",
                    }),
                    source="llm",
                    summary=llm_out.get("summary", ""),
                    provenance=provenance or {},
                )
        except Exception:
            pass  # Fall through to rule-based

        # ── Rule-based fallback ────────────────────────────────────────────
        return _rule_based_plan(action_signature, matched_pattern)
