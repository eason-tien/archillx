from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECTIONS = {"all", "guard", "baseline", "artifacts"}


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _ensure_dir() -> Path:
    out = Path("evidence/evolution/reviews")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _title(section: str) -> str:
    return {
        "all": "Full review bundle",
        "guard": "Guard review",
        "baseline": "Baseline review",
        "artifacts": "Artifact review",
    }.get(section, section)


def _md(payload: dict[str, Any]) -> str:
    sec = payload["section"]
    lines = [
        f"# {_title(sec)}",
        "",
        f"- proposal_id: `{payload['proposal_id']}`",
        f"- generated_at: `{payload['generated_at']}`",
        f"- section: `{sec}`",
        "",
        "## Summary",
        "",
        "```json",
        __import__("json").dumps(payload.get("summary", {}), ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    if payload.get("content") is not None:
        lines += [
            "## Content",
            "",
            "```json",
            __import__("json").dumps(payload["content"], ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    return "\n".join(lines)


def _html(payload: dict[str, Any]) -> str:
    import json
    sec = payload["section"]
    summary = json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2)
    content = json.dumps(payload.get("content", {}), ensure_ascii=False, indent=2)
    title = _title(sec)
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background:#f8fafc; color:#111827; }}
.card {{ background:white; border:1px solid #e5e7eb; border-radius:12px; padding:16px; margin-bottom:16px; }}
pre {{ background:#111827; color:#e5e7eb; padding:12px; border-radius:8px; overflow:auto; }}
</style></head>
<body>
<h1>{title}</h1>
<div class='card'><strong>Proposal:</strong> {payload['proposal_id']}<br><strong>Generated:</strong> {payload['generated_at']}<br><strong>Section:</strong> {sec}</div>
<div class='card'><h2>Summary</h2><pre>{summary}</pre></div>
<div class='card'><h2>Content</h2><pre>{content}</pre></div>
</body></html>"""


def render_review_export(proposal_id: str, section: str, summary: dict[str, Any], content: dict[str, Any]) -> dict[str, Any]:
    if section not in SECTIONS:
        raise ValueError(f"Unsupported section: {section}")
    base = _ensure_dir()
    stamp = _now_stamp()
    stem = f"review_{proposal_id}_{section}_{stamp}"
    payload = {
        "proposal_id": proposal_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "section": section,
        "summary": summary,
        "content": content,
    }
    j = base / f"{stem}.json"
    m = base / f"{stem}.md"
    h = base / f"{stem}.html"
    import json
    j.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    m.write_text(_md(payload), encoding="utf-8")
    h.write_text(_html(payload), encoding="utf-8")
    return {"json": str(j), "markdown": str(m), "html": str(h), "section": section}
