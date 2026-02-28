from __future__ import annotations

from typing import List

from .schemas import EvolutionFinding, EvolutionSignalSnapshot


HIGH_RISK_SUBJECTS = {"sandbox", "acl", "auth", "migration", "code_exec", "file_ops"}


def classify_findings(snapshot: EvolutionSignalSnapshot) -> List[EvolutionFinding]:
    findings: list[EvolutionFinding] = []
    readiness = snapshot.readiness or {}
    migration = snapshot.migration or {}
    aggregate = (snapshot.telemetry or {}).get("aggregate", {})
    history = ((snapshot.telemetry or {}).get("history", {}) or {}).get("windows", {})
    last_300 = history.get("last_300s", {})
    audit_summary = snapshot.audit_summary or {}
    gate_summary = snapshot.gate_summary or {}

    if readiness.get("status") != "ready":
        findings.append(EvolutionFinding(
            category="operability",
            severity="critical",
            subject="readiness",
            signal="ready.status",
            summary="System readiness is degraded and requires operator attention.",
            value=readiness.get("status"),
            confidence=0.98,
            evidence=["/v1/ready"],
        ))

    if migration.get("status") not in ("head", "disabled"):
        findings.append(EvolutionFinding(
            category="migration_gap",
            severity="high",
            subject="migration",
            signal="migration.status",
            summary="Database migration state is behind or unknown.",
            value=migration.get("status"),
            confidence=0.95,
            evidence=["/v1/migration/state"],
        ))

    http5xx = (((last_300.get("http") or {}).get("status") or {}).get("5xx") or 0)
    if http5xx > 0:
        findings.append(EvolutionFinding(
            category="stability",
            severity="high" if http5xx >= 5 else "medium",
            subject="http",
            signal="history.last_300s.http.status.5xx",
            summary="Recent HTTP 5xx responses detected in the last 5 minutes.",
            value=int(http5xx),
            confidence=0.88,
            evidence=["/v1/telemetry"],
        ))

    skill_failures = (((aggregate.get("skills") or {}).get("totals") or {}).get("failure_total") or 0)
    if skill_failures > 0:
        findings.append(EvolutionFinding(
            category="reliability",
            severity="medium",
            subject="skills",
            signal="skills.failure_total",
            summary="Skill failures have been observed and should be triaged.",
            value=int(skill_failures),
            confidence=0.82,
            evidence=["/v1/telemetry"],
        ))

    sandbox_blocked = (((last_300.get("sandbox") or {}).get("blocked_total")) or 0)
    if sandbox_blocked > 0:
        findings.append(EvolutionFinding(
            category="security",
            severity="medium",
            subject="sandbox",
            signal="history.last_300s.sandbox.blocked_total",
            summary="Sandbox blocked executions were observed recently; review policy or callers.",
            value=int(sandbox_blocked),
            confidence=0.8,
            evidence=["/v1/telemetry", "/v1/audit/summary"],
        ))

    blocked_decisions = (audit_summary.get("by_decision") or {}).get("BLOCKED", 0)
    if blocked_decisions > 0:
        findings.append(EvolutionFinding(
            category="security",
            severity="medium",
            subject="audit",
            signal="audit.by_decision.BLOCKED",
            summary="Security audit shows blocked decisions that may merit pattern review.",
            value=int(blocked_decisions),
            confidence=0.74,
            evidence=["/v1/audit/summary"],
        ))

    rel_failed = ((gate_summary.get("release") or {}).get("failed") or 0)
    rb_failed = ((gate_summary.get("rollback") or {}).get("failed") or 0)
    if rel_failed or rb_failed:
        findings.append(EvolutionFinding(
            category="deployment_gap",
            severity="high",
            subject="release_gate",
            signal="gate_summary.failures",
            summary="Release or rollback gate failures exist in recent evidence and should be investigated before upgrades.",
            value={"release_failed": int(rel_failed), "rollback_failed": int(rb_failed)},
            confidence=0.9,
            evidence=["evidence/releases", "evidence/dashboards"],
        ))

    return findings
