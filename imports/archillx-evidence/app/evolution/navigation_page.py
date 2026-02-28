from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

from .proposal_store import _ensure


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def render_markdown(payload: dict[str, Any]) -> str:
    latest = payload.get("latest", {}) or {}
    docs = payload.get("docs", []) or []
    routes = payload.get("routes", []) or []
    nav = payload.get("navigation", {}) or {}
    lines = [
        "# Evolution Navigation Page",
        "",
        f"Generated at: {payload.get('generated_at')}",
        "",
        "## Primary Routes",
        "",
    ]
    lines.extend([f"- `{r}`" for r in routes])
    lines.extend(["", "## Docs", ""])
    lines.extend([f"- {d.get('name')}: `{d.get('path')}`" for d in docs])
    lines.extend(["", "## Latest Objects", ""])
    lines.extend([f"- {k}: `{v}`" for k, v in latest.items()])
    lines.extend(["", "## Evidence Navigation", ""])
    for k, v in nav.items():
        lines.append(f"- **{k}**: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines).strip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    def route_list(items: list[str]) -> str:
        return "".join(f"<li><code>{html.escape(x)}</code></li>" for x in items) or "<li>None</li>"

    def doc_list(items: list[dict[str, Any]]) -> str:
        return "".join(
            f"<li><strong>{html.escape(str(d.get('name')))}</strong><br><code>{html.escape(str(d.get('path')))}</code></li>"
            for d in items
        ) or "<li>None</li>"

    def kv_list(mapping: dict[str, Any]) -> str:
        return "".join(
            f"<li><strong>{html.escape(str(k))}</strong>: <code>{html.escape(str(v))}</code></li>"
            for k, v in mapping.items()
        ) or "<li>None</li>"

    latest = payload.get("latest", {}) or {}
    docs = payload.get("docs", []) or []
    routes = payload.get("routes", []) or []
    nav = payload.get("navigation", {}) or {}
    bundle = payload.get("bundle_paths", {}) or {}
    summary = payload.get("summary", {}) or {}
    pipeline = summary.get("pipeline", {}) or {}
    proposal_status = summary.get("proposal_status", {}) or {}

    def mini_cards(mapping: dict[str, Any]) -> str:
        cards = []
        for key, value in list(mapping.items())[:6]:
            cards.append(
                f"<div class='mini-card'><div class='mini-title'>{html.escape(str(key))}</div><div class='mini-value'>{html.escape(str(value))}</div></div>"
            )
        return "".join(cards) or "<div class='mini-card'><div class='mini-title'>None</div><div class='mini-value'>0</div></div>"

    badges = (
        f"<span class='badge'>Generated: {html.escape(str(payload.get('generated_at')))}</span>"
        f"<span class='badge'>Latest proposal: {html.escape(str(latest.get('proposal_id')))}</span>"
        f"<span class='badge'>Latest action: {html.escape(str(latest.get('action_id')))}</span>"
        f"<span class='badge'>Latest schedule: {html.escape(str(latest.get('schedule_cycle_id')))}</span>"
    )

    html_out = """<!doctype html>
<html><head><meta charset=\"utf-8\"><title>Evolution Navigation Page</title>
<style>
:root{--bg:#f6f8fb;--card:#fff;--border:#d8dee9;--text:#17212b;--muted:#5f6b7a;--accent:#2f6feb;}
body{font-family:Arial,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:24px;line-height:1.5}
.hero{background:linear-gradient(135deg,#ffffff,#eef4ff);border:1px solid var(--border);border-radius:16px;padding:18px 20px;margin-bottom:18px;box-shadow:0 8px 24px rgba(15,23,42,.06)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.badge{background:#eaf2ff;color:#1f4b99;border:1px solid #c7dbff;border-radius:999px;padding:4px 10px;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(320px,1fr));gap:16px}.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;box-shadow:0 4px 14px rgba(15,23,42,.04)}.wide{grid-column:1 / -1}
ul{margin:0;padding-left:20px}li{margin:4px 0} code{background:#f3f4f6;padding:2px 6px;border-radius:6px}
.section-note{font-size:13px;color:var(--muted);margin-bottom:10px}.mini-grid{display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:10px}.mini-card{border:1px solid var(--border);border-radius:12px;padding:12px;background:#fbfcfe}.mini-title{font-size:12px;color:var(--muted)}.mini-value{font-size:24px;font-weight:700;margin-top:4px}
@media (max-width: 960px){.grid{grid-template-columns:1fr}.mini-grid{grid-template-columns:1fr 1fr}}
</style>
</head><body>
<div class=\"hero\">
  <h1>Evolution Navigation Page</h1>
  <p>Subsystem landing page for operators, reviewers, and approvers. Use this page to move between summary, evidence, docs, and recent workflow objects.</p>
  <div class=\"badges\">__BADGES__</div>
</div>
<div class=\"grid\">
  <div class=\"card\">
    <h2>Primary routes</h2>
    <div class=\"section-note\">Start here to inspect the current evolution pipeline and governance state.</div>
    <ul>__ROUTES__</ul>
  </div>
  <div class=\"card\">
    <h2>Linked docs</h2>
    <div class=\"section-note\">Operator-facing references for governance, dashboard use, evidence browsing, and runbook execution.</div>
    <ul>__DOCS__</ul>
  </div>
  <div class=\"card\">
    <h2>Pipeline snapshot</h2>
    <div class=\"section-note\">High-value pipeline KPIs extracted from the current summary.</div>
    <div class=\"mini-grid\">__PIPELINE__</div>
  </div>
  <div class=\"card\">
    <h2>Proposal status</h2>
    <div class=\"section-note\">Quick status distribution for proposals under review, approval, or rollout.</div>
    <div class=\"mini-grid\">__PROPOSAL_STATUS__</div>
  </div>
  <div class=\"card\">
    <h2>Latest objects</h2>
    <div class=\"section-note\">Recent IDs for quick drill-down into evidence and workflow state.</div>
    <ul>__LATEST__</ul>
  </div>
  <div class=\"card\">
    <h2>Bundle paths</h2>
    <div class=\"section-note\">Recently rendered overview/dashboard bundle paths for review and handoff.</div>
    <ul>__BUNDLE__</ul>
  </div>
  <div class=\"card wide\">
    <h2>Evidence navigation</h2>
    <div class=\"section-note\">Shortcut navigation into evidence graph anchored on the latest proposal / guard / baseline / action records.</div>
    <ul>__NAV__</ul>
  </div>
</div>
</body></html>"""
    return (
        html_out.replace("__BADGES__", badges)
        .replace("__ROUTES__", route_list(routes))
        .replace("__DOCS__", doc_list(docs))
        .replace("__PIPELINE__", mini_cards(pipeline))
        .replace("__PROPOSAL_STATUS__", mini_cards(proposal_status))
        .replace("__LATEST__", kv_list(latest))
        .replace("__BUNDLE__", kv_list(bundle))
        .replace("__NAV__", kv_list(nav))
    )


def write_navigation_bundle(payload: dict[str, Any]) -> dict[str, str]:
    directory = _ensure("dashboards")
    stamp = _now_stamp()
    base = directory / f"evolution_nav_{stamp}"
    json_path = base.with_suffix('.json')
    md_path = base.with_suffix('.md')
    html_path = base.with_suffix('.html')
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    md_path.write_text(render_markdown(payload), encoding='utf-8')
    html_path.write_text(render_html(payload), encoding='utf-8')
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}
