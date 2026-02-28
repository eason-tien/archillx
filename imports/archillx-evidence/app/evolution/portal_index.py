from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

from .proposal_store import _ensure


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def render_markdown(payload: dict[str, Any]) -> str:
    blocks = payload.get("blocks", {}) or {}
    lines = [
        "# Evolution Portal Index",
        "",
        f"Generated at: {payload.get('generated_at')}",
        "",
        "## Quick sections",
        "",
        "- Overview & quick actions",
        "- Operations lane",
        "- Review & approval lane",
        "- Evidence & artifacts lane",
        "- Dashboard lane",
        "- Runbook lane",
        "",
    ]
    for title, items in blocks.items():
        lines.append(f"## {title.replace('_', ' ').title()}")
        lines.append("")
        if isinstance(items, list):
            if items and isinstance(items[0], dict):
                for item in items:
                    label = item.get("label") or item.get("name") or item.get("title") or "item"
                    target = item.get("target") or item.get("path") or item.get("route") or item.get("value") or ""
                    lines.append(f"- **{label}**: `{target}`")
            else:
                lines.extend([f"- `{x}`" for x in items])
        elif isinstance(items, dict):
            for k, v in items.items():
                lines.append(f"- **{k}**: `{v}`")
        else:
            lines.append(f"- `{items}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    blocks = payload.get("blocks", {}) or {}
    summary = payload.get("summary", {}) or {}
    latest = summary.get("latest", {}) or {}
    pipeline = summary.get("pipeline", {}) or {}
    latest_nav = blocks.get("latest_navigation", {}) or {}

    def list_items(items: Any) -> str:
        if isinstance(items, list):
            if items and isinstance(items[0], dict):
                out = []
                for item in items:
                    label = item.get("label") or item.get("name") or item.get("title") or "item"
                    target = item.get("target") or item.get("path") or item.get("route") or item.get("value") or ""
                    out.append(
                        f"<li><strong>{html.escape(str(label))}</strong><br><code>{html.escape(str(target))}</code></li>"
                    )
                return "".join(out) or "<li>None</li>"
            return "".join(f"<li><code>{html.escape(str(x))}</code></li>" for x in items) or "<li>None</li>"
        if isinstance(items, dict):
            return "".join(
                f"<li><strong>{html.escape(str(k))}</strong>: <code>{html.escape(str(v))}</code></li>"
                for k, v in items.items()
            ) or "<li>None</li>"
        return f"<li><code>{html.escape(str(items))}</code></li>"

    def metric_cards(mapping: dict[str, Any], keys: list[tuple[str, str]]) -> str:
        cards: list[str] = []
        for key, label in keys:
            value = mapping.get(key)
            cards.append(
                f"<div class='metric-card'><div class='metric-label'>{html.escape(label)}</div><div class='metric-value'>{html.escape(str(value))}</div></div>"
            )
        return "".join(cards)

    api = blocks.get("api_entrypoints", [])
    evidence = blocks.get("evidence_entrypoints", [])
    dashboards = blocks.get("dashboard_entrypoints", [])
    runbooks = blocks.get("runbook_entrypoints", [])
    flows = blocks.get("recommended_flows", [])

    html_doc = """<!doctype html>
<html><head><meta charset='utf-8'><title>Evolution Portal</title>
<style>
:root{--bg:#f6f8fb;--card:#fff;--border:#d8dee9;--text:#17212b;--muted:#5f6b7a;--accent:#2f6feb}
body{font-family:Arial,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:24px;line-height:1.5}
.hero{background:linear-gradient(135deg,#ffffff,#eef4ff);border:1px solid var(--border);border-radius:18px;padding:20px 22px;margin-bottom:18px;box-shadow:0 8px 24px rgba(15,23,42,.06)}
.hero p{margin:8px 0 0 0;color:var(--muted)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.badge{background:#eaf2ff;color:#1f4b99;border:1px solid #c7dbff;border-radius:999px;padding:4px 10px;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px;box-shadow:0 4px 14px rgba(15,23,42,.04)}
.span-4{grid-column:span 4}.span-6{grid-column:span 6}.span-12{grid-column:span 12}
.section-note{font-size:13px;color:var(--muted);margin-bottom:10px}
ul{margin:0;padding-left:20px}li{margin:6px 0} code{background:#f3f4f6;padding:2px 6px;border-radius:6px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px}.metric-card{border:1px solid var(--border);border-radius:12px;padding:12px;background:#fbfcfe}.metric-label{font-size:12px;color:var(--muted)}.metric-value{font-size:24px;font-weight:700;margin-top:4px}
.lane-title{display:flex;align-items:center;justify-content:space-between}.pill{font-size:12px;border-radius:999px;padding:4px 8px;border:1px solid var(--border);color:var(--muted)}
.callout{border-left:4px solid var(--accent);padding:10px 12px;background:#f8fbff;border-radius:10px;color:#28476f}
@media (max-width: 1000px){.grid{grid-template-columns:1fr}.span-4,.span-6,.span-12{grid-column:1}.metrics{grid-template-columns:repeat(2,minmax(120px,1fr))}}
</style>
</head><body>
<div class='hero'>
  <h1>Evolution Portal</h1>
  <p>Multi-section landing page for the evolution subsystem. Start from overview, then move into operations, review, evidence, dashboard, and runbook lanes.</p>
  <div class='badges'>
    <span class='badge'>Generated: __GENERATED__</span>
    <span class='badge'>Latest proposal: __LATEST_PROPOSAL__</span>
    <span class='badge'>Latest action: __LATEST_ACTION__</span>
    <span class='badge'>Latest schedule: __LATEST_SCHEDULE__</span>
  </div>
</div>
<div class='grid'>
  <section class='card span-12'>
    <div class='lane-title'><h2>Overview & quick actions</h2><span class='pill'>Entry lane</span></div>
    <div class='section-note'>Use these KPIs to decide whether to inspect, review, approve, or halt changes.</div>
    <div class='metrics'>__METRICS__</div>
    <div class='callout' style='margin-top:12px'>Recommended start: summary → dashboard render → evidence index → proposal navigation → runbook.</div>
  </section>
  <section class='card span-6'>
    <div class='lane-title'><h2>Operations lane</h2><span class='pill'>Operator</span></div>
    <div class='section-note'>Operational entrypoints for current state, rendering bundles, and automation cycles.</div>
    <ul>__API__</ul>
  </section>
  <section class='card span-6'>
    <div class='lane-title'><h2>Review & approval lane</h2><span class='pill'>Reviewer / Approver</span></div>
    <div class='section-note'>Use these guided flows when triaging proposals, evaluating evidence, and making decisions.</div>
    <ul>__FLOWS__</ul>
  </section>
  <section class='card span-4'>
    <div class='lane-title'><h2>Evidence lane</h2><span class='pill'>Traceability</span></div>
    <div class='section-note'>Jump into evidence indexes, proposal navigation, and latest linked artifacts.</div>
    <ul>__EVIDENCE__</ul>
  </section>
  <section class='card span-4'>
    <div class='lane-title'><h2>Dashboard lane</h2><span class='pill'>Bundles</span></div>
    <div class='section-note'>Render and inspect dashboard, navigation, portal, and subsystem bundles.</div>
    <ul>__DASHBOARDS__</ul>
  </section>
  <section class='card span-4'>
    <div class='lane-title'><h2>Runbook lane</h2><span class='pill'>Guidance</span></div>
    <div class='section-note'>Human-facing docs for governance, operations, review cadence, and decision boundaries.</div>
    <ul>__RUNBOOKS__</ul>
  </section>
  <section class='card span-6'>
    <div class='lane-title'><h2>Latest linked objects</h2><span class='pill'>Recent state</span></div>
    <ul>__LATEST_NAV__</ul>
  </section>
  <section class='card span-6'>
    <div class='lane-title'><h2>Operator guidance</h2><span class='pill'>Suggested order</span></div>
    <div class='callout'>If pending approval is non-zero, review proposal list and guard/baseline evidence first. If regression rate is elevated, stop auto-apply and inspect baseline evidence before proceeding.</div>
  </section>
</div>
</body></html>"""

    return (
        html_doc.replace("__GENERATED__", html.escape(str(payload.get("generated_at"))))
        .replace("__LATEST_PROPOSAL__", html.escape(str(latest.get("proposal_id"))))
        .replace("__LATEST_ACTION__", html.escape(str(latest.get("action_id"))))
        .replace("__LATEST_SCHEDULE__", html.escape(str(latest.get("schedule_cycle_id"))))
        .replace(
            "__METRICS__",
            metric_cards(
                pipeline,
                [
                    ("pending_approval", "Pending approval"),
                    ("actionable", "Actionable"),
                    ("guard_pass_rate", "Guard pass rate"),
                    ("regression_rate", "Regression rate"),
                ],
            ),
        )
        .replace("__API__", list_items(api))
        .replace("__FLOWS__", list_items(flows))
        .replace("__EVIDENCE__", list_items(evidence))
        .replace("__DASHBOARDS__", list_items(dashboards))
        .replace("__RUNBOOKS__", list_items(runbooks))
        .replace("__LATEST_NAV__", list_items(latest_nav))
    )


def write_portal_bundle(payload: dict[str, Any]) -> dict[str, str]:
    directory = _ensure("dashboards")
    stamp = _now_stamp()
    base = directory / f"evolution_portal_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    html_path = base.with_suffix(".html")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}
