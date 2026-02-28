from __future__ import annotations

from dataclasses import dataclass
from typing import Any


HIGH_RISK_PERMISSIONS = {"exec", "filesystem"}


class SkillAccessDenied(Exception):
    pass


@dataclass
class SkillAccessContext:
    source: str = "unknown"
    role: str = "anonymous"
    session_id: str | None = None
    task_id: str | None = None


def _normalize_context(context: dict[str, Any] | None) -> SkillAccessContext:
    ctx = context or {}
    return SkillAccessContext(
        source=str(ctx.get("source") or "unknown"),
        role=str(ctx.get("role") or "anonymous"),
        session_id=str(ctx.get("session_id")) if ctx.get("session_id") is not None else None,
        task_id=str(ctx.get("task_id")) if ctx.get("task_id") is not None else None,
    )


def _as_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).strip() for v in value if str(v).strip()}
    return {str(value).strip()}


def check_skill_access(name: str, manifest: dict[str, Any] | None, context: dict[str, Any] | None) -> None:
    manifest = manifest or {}
    ctx = _normalize_context(context)
    acl = manifest.get("acl") or {}

    allowed_roles = _as_set(acl.get("allow_roles"))
    allowed_sources = _as_set(acl.get("allow_sources"))
    denied_sources = _as_set(acl.get("deny_sources"))
    permissions = _as_set(manifest.get("permissions"))

    if ctx.source in denied_sources:
        raise SkillAccessDenied(f"Skill '{name}' denied for source '{ctx.source}'.")

    if allowed_sources and ctx.source not in allowed_sources:
        raise SkillAccessDenied(f"Skill '{name}' not allowed from source '{ctx.source}'.")

    if allowed_roles and ctx.role not in allowed_roles:
        raise SkillAccessDenied(f"Skill '{name}' requires one of roles: {sorted(allowed_roles)}.")

    # Safe default for high-risk permissions when ACL is enabled but manifest is loose.
    if permissions & HIGH_RISK_PERMISSIONS:
        if ctx.role not in {"admin", "system"}:
            raise SkillAccessDenied(
                f"Skill '{name}' requires admin/system role because it has high-risk permissions: {sorted(permissions & HIGH_RISK_PERMISSIONS)}."
            )
