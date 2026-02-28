from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import EvolutionProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_dir(proposal_id: str) -> Path:
    path = Path("evidence/evolution/artifacts") / proposal_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _comment_prefix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".py", ".sh", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg", ".env", ""} or path.name == "Dockerfile":
        return "#"
    if suffix in {".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".swift", ".kt", ".php"}:
        return "//"
    if suffix in {".sql", ".lua"}:
        return "--"
    if suffix in {".html", ".md"}:
        return "<!--"
    if suffix == ".css":
        return "/*"
    return "#"


def _comment_lines(path_str: str, proposal: EvolutionProposal, action: str, rationale: str | None) -> list[str]:
    path = Path(path_str)
    prefix = _comment_prefix(path)
    suffix = " -->" if prefix == "<!--" else (" */" if prefix == "/*" else "")
    rows = [
        f"{prefix} proposal-id: {proposal.proposal_id}{suffix}",
        f"{prefix} subject: {proposal.source_subject}{suffix}",
        f"{prefix} action: {action}{suffix}",
    ]
    if rationale:
        rows.append(f"{prefix} rationale: {rationale}{suffix}")
    rows.append("")
    return rows


def _render_target_after(path_str: str, proposal: EvolutionProposal, action: str, rationale: str | None) -> tuple[list[str], list[str]]:
    path = Path(path_str)
    before_text = path.read_text(encoding="utf-8") if path.exists() else ""
    before_lines = before_text.splitlines()
    note_lines = _comment_lines(path_str, proposal, action, rationale)

    if action == "add" and not before_lines:
        body = note_lines + [f"Generated artifact scaffold for {proposal.title}."]
        return before_lines, body

    if before_lines:
        after_lines = before_lines.copy()
        insert_at = min(len(after_lines), 5)
        after_lines[insert_at:insert_at] = note_lines
        return before_lines, after_lines

    body = note_lines + [f"Review required for {proposal.title}."]
    return before_lines, body


def _build_unified_diff(proposal: EvolutionProposal) -> str:
    chunks: list[str] = []
    for change in proposal.suggested_changes:
        before_lines, after_lines = _render_target_after(change.file, proposal, change.action, change.rationale)
        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{change.file}",
                tofile=f"b/{change.file}",
                lineterm="",
            )
        )
        if not diff_lines:
            diff_lines = [
                f"--- a/{change.file}",
                f"+++ b/{change.file}",
                "@@ -0,0 +1 @@",
                f"+# reviewed-noop: {proposal.proposal_id}",
            ]
        chunks.extend(diff_lines)
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def render_patch_artifacts(proposal: EvolutionProposal) -> dict[str, str]:
    artifact_dir = _artifact_dir(proposal.proposal_id)
    patch_path = artifact_dir / "patch.diff"
    pr_path = artifact_dir / "pr_draft.md"
    pr_title_path = artifact_dir / "pr_title.txt"
    commit_path = artifact_dir / "commit_message.txt"
    tests_path = artifact_dir / "tests_to_add.md"
    rollout_path = artifact_dir / "rollout_notes.md"
    risk_path = artifact_dir / "risk_assessment.json"
    manifest_path = artifact_dir / "manifest.json"

    patch_path.write_text(_build_unified_diff(proposal), encoding="utf-8")

    pr_title = f"[{proposal.risk.risk_level.upper()}] {proposal.title}"
    pr_title_path.write_text(pr_title + "\n", encoding="utf-8")

    pr_lines = [
        f"# PR Draft — {proposal.title}",
        "",
        f"PR Title: `{pr_title}`",
        f"Proposal ID: `{proposal.proposal_id}`",
        f"Created at: `{_now_iso()}`",
        "",
        "## Summary",
        proposal.summary,
        "",
        "## Suggested changes",
        *[f"- `{c.file}` ({c.action}) — {c.rationale or 'n/a'}" for c in proposal.suggested_changes],
        "",
        "## Validation plan",
        *[f"- {t}" for t in (proposal.tests_to_add or ["Add targeted regression coverage before merge."])],
        "",
        "## Risk",
        f"- Level: **{proposal.risk.risk_level}**",
        f"- Score: **{proposal.risk.risk_score}**",
        *[f"- Factor: {f}" for f in proposal.risk.factors],
        "",
        "## Rollout notes",
        *[f"- {n}" for n in (proposal.rollout_notes or ["No rollout notes."])],
        "",
        "## Reviewer checklist",
        "- [ ] Proposed scope matches the finding / plan item",
        "- [ ] Added or updated targeted tests",
        "- [ ] Guard / baseline outputs reviewed",
        "- [ ] Rollback path is clear",
    ]
    pr_path.write_text("\n".join(pr_lines).rstrip() + "\n", encoding="utf-8")

    commit_lines = [
        f"evolution: {proposal.source_subject} remediation",
        "",
        f"proposal-id: {proposal.proposal_id}",
        f"risk-level: {proposal.risk.risk_level}",
        "",
        proposal.summary,
        "",
        "Suggested scope:",
        *[f"- {c.file} ({c.action})" for c in proposal.suggested_changes],
    ]
    commit_path.write_text("\n".join(commit_lines).rstrip() + "\n", encoding="utf-8")

    tests_lines = ["# Tests to add", "", *[f"- {t}" for t in (proposal.tests_to_add or ["No targeted test suggestions."])]]
    tests_path.write_text("\n".join(tests_lines).rstrip() + "\n", encoding="utf-8")

    rollout_lines = ["# Rollout notes", "", *[f"- {n}" for n in (proposal.rollout_notes or ["No rollout notes."])]]
    rollout_path.write_text("\n".join(rollout_lines).rstrip() + "\n", encoding="utf-8")

    risk_payload = {
        "proposal_id": proposal.proposal_id,
        "risk_score": proposal.risk.risk_score,
        "risk_level": proposal.risk.risk_level,
        "factors": proposal.risk.factors,
        "auto_apply_allowed": proposal.risk.auto_apply_allowed,
        "approval_required": proposal.approval_required,
    }
    risk_path.write_text(json.dumps(risk_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = {
        "proposal_id": proposal.proposal_id,
        "generated_at": _now_iso(),
        "paths": {
            "patch": str(patch_path),
            "pr_draft": str(pr_path),
            "pr_title": str(pr_title_path),
            "commit_message": str(commit_path),
            "tests": str(tests_path),
            "rollout": str(rollout_path),
            "risk": str(risk_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"dir": str(artifact_dir), **manifest["paths"], "manifest": str(manifest_path)}


def read_patch_artifact_preview(paths: dict[str, str]) -> dict[str, str]:
    preview: dict[str, str] = {}
    keys = ["patch", "pr_draft", "pr_title", "commit_message", "tests", "rollout"]
    for key in keys:
        path = paths.get(key)
        if not path:
            continue
        try:
            preview[key] = Path(path).read_text(encoding="utf-8")
        except Exception:
            preview[key] = ""
    return preview


def read_manifest_summary(paths: dict[str, str]) -> dict:
    manifest_path = paths.get("manifest")
    if not manifest_path:
        return {}
    try:
        payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    manifest_paths = payload.get("paths") or {}
    return {
        "proposal_id": payload.get("proposal_id"),
        "generated_at": payload.get("generated_at"),
        "artifact_count": len(manifest_paths),
        "artifact_keys": sorted(manifest_paths.keys()),
        "paths": manifest_paths,
    }
