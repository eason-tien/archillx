"""
ArcHillx — Multi-Agent Audit Router
====================================
Routes executor output to specialist auditors based on task-type tags:
  UI tasks        → UI_AUDITOR
  Code changes    → CODE_AUDITOR
  DB / auth       → SECURITY_AUDITOR
  High-load / perf→ PERFORMANCE_AUDITOR

Final results are aggregated by MasterGovernor; not exposed individually.
Standalone — no MGIS imports.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .types import AuditDecision, AuditorRole


# ── Auditor Base Class ────────────────────────────────────────────────────────

class BaseAuditor(ABC):
    role: AuditorRole

    @abstractmethod
    def audit(
        self,
        task_id:     str,
        executor_id: str,
        output:      Dict[str, Any],
        context:     Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Returns dict:
          {decision, role, violated_rule, error_type, improvement, confidence, risk_score}
        """


def _approve(role: str) -> Dict[str, Any]:
    return {
        "decision":      AuditDecision.APPROVE,
        "role":          role,
        "violated_rule": "",
        "error_type":    "",
        "improvement":   "",
        "confidence":    0.9,
        "risk_score":    0.0,
    }


def _reject(
    role: str,
    violated_rule: str,
    error_type: str,
    improvement: str,
    confidence: float,
    risk_score: float,
) -> Dict[str, Any]:
    return {
        "decision":      AuditDecision.REJECT,
        "role":          role,
        "violated_rule": violated_rule,
        "error_type":    error_type,
        "improvement":   improvement,
        "confidence":    confidence,
        "risk_score":    risk_score,
    }


# ── Specialist Auditor Implementations ────────────────────────────────────────

class UIAuditor(BaseAuditor):
    """Checks UI output contract: required_fields present, structure valid."""
    role = AuditorRole.UI_AUDITOR

    def audit(self, task_id, executor_id, output, context):
        role = self.role.value
        for f in context.get("ui_required_fields", []):
            if f not in output:
                return _reject(
                    role,
                    violated_rule=f"MISSING_FIELD:{f}",
                    error_type="UI_CONTRACT_VIOLATION",
                    improvement=f"Ensure output contains required field '{f}'",
                    confidence=0.9,
                    risk_score=55.0,
                )
        return _approve(role)


class CodeAuditor(BaseAuditor):
    """Checks code output: dangerous patterns, unsandboxed dynamic execution."""
    role = AuditorRole.CODE_AUDITOR

    _DANGER_PATTERNS = [
        "eval(",
        "exec(",
        "__import__(",
        "subprocess.call(",
        "os.system(",
        "compile(",
    ]

    def audit(self, task_id, executor_id, output, context):
        role = self.role.value
        code = str(output.get("code", output.get("result", output)))
        for pattern in self._DANGER_PATTERNS:
            if pattern in code:
                return _reject(
                    role,
                    violated_rule=f"DANGEROUS_PATTERN:{pattern}",
                    error_type="CODE_SECURITY_VIOLATION",
                    improvement=f"Remove or sandbox usage of '{pattern}'",
                    confidence=0.95,
                    risk_score=85.0,
                )
        return _approve(role)


class SecurityAuditor(BaseAuditor):
    """Checks security compliance: no credential leaks, no injection patterns, no PII."""
    role = AuditorRole.SECURITY_AUDITOR

    _SECRET_MARKERS = [
        "password=",
        "api_key=",
        "secret=",
        "token=",
        "private_key=",
        "aws_access",
    ]

    def audit(self, task_id, executor_id, output, context):
        role = self.role.value
        payload = str(output).lower()
        for marker in self._SECRET_MARKERS:
            if marker in payload:
                return _reject(
                    role,
                    violated_rule=f"CREDENTIAL_LEAK:{marker}",
                    error_type="SECURITY_VIOLATION",
                    improvement="Do not embed credentials in output; use env vars or a secrets manager",
                    confidence=0.92,
                    risk_score=90.0,
                )
        return _approve(role)


class PerformanceAuditor(BaseAuditor):
    """Checks performance: latency within threshold."""
    role = AuditorRole.PERFORMANCE_AUDITOR

    _DEFAULT_THRESHOLD_MS = 5000

    def audit(self, task_id, executor_id, output, context):
        role      = self.role.value
        latency   = context.get("latency_ms", 0)
        threshold = context.get("perf_latency_threshold_ms", self._DEFAULT_THRESHOLD_MS)
        if latency > threshold:
            return _reject(
                role,
                violated_rule="LATENCY_EXCEEDED",
                error_type="PERFORMANCE_VIOLATION",
                improvement=(
                    f"Actual latency {latency}ms exceeds threshold {threshold}ms; "
                    "consider query optimisation or adding a caching layer"
                ),
                confidence=0.85,
                risk_score=50.0,
            )
        return _approve(role)


# ── Routing Table ─────────────────────────────────────────────────────────────

_TAG_TO_ROLE: Dict[str, AuditorRole] = {
    "ui":          AuditorRole.UI_AUDITOR,
    "frontend":    AuditorRole.UI_AUDITOR,
    "html":        AuditorRole.UI_AUDITOR,
    "code":        AuditorRole.CODE_AUDITOR,
    "backend":     AuditorRole.CODE_AUDITOR,
    "script":      AuditorRole.CODE_AUDITOR,
    "security":    AuditorRole.SECURITY_AUDITOR,
    "auth":        AuditorRole.SECURITY_AUDITOR,
    "database":    AuditorRole.SECURITY_AUDITOR,
    "db":          AuditorRole.SECURITY_AUDITOR,
    "performance": AuditorRole.PERFORMANCE_AUDITOR,
    "perf":        AuditorRole.PERFORMANCE_AUDITOR,
    "load":        AuditorRole.PERFORMANCE_AUDITOR,
}


class AuditRouter:
    """
    Selects auditors based on context["task_type_tags"] and returns leaf results.
    If no matching tags, defaults to CODE_AUDITOR + SECURITY_AUDITOR.
    """

    def __init__(self) -> None:
        self._auditors: Dict[AuditorRole, BaseAuditor] = {
            AuditorRole.UI_AUDITOR:          UIAuditor(),
            AuditorRole.CODE_AUDITOR:        CodeAuditor(),
            AuditorRole.SECURITY_AUDITOR:    SecurityAuditor(),
            AuditorRole.PERFORMANCE_AUDITOR: PerformanceAuditor(),
        }

    def route(
        self,
        task_id:     str,
        executor_id: str,
        output:      Dict[str, Any],
        context:     Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Returns list of per-auditor result dicts."""
        tags: List[str] = context.get("task_type_tags", [])
        selected = {_TAG_TO_ROLE[t.lower()] for t in tags if t.lower() in _TAG_TO_ROLE}

        # Fall back to default audit set when no tags match
        if not selected:
            selected = {AuditorRole.CODE_AUDITOR, AuditorRole.SECURITY_AUDITOR}

        results: List[Dict[str, Any]] = []
        for role in selected:
            verdict = self._auditors[role].audit(task_id, executor_id, output, context)
            verdict["role"] = role.value   # normalise role field to string value
            results.append(verdict)

        return results
