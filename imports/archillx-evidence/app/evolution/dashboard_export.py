from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _dashboard_dir() -> Path:
    p = Path(settings.evidence_dir).resolve() / "evolution" / "dashboards"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _top_items(mapping: dict[str, Any], limit: int = 5):
    items = []
    for k, v in (mapping or {}).items():
        try:
            items.append((str(k), int(v)))
        except Exception:
            continue
    items.sort(key=lambda x: (-x[1], x[0]))
    return items[:limit]


def render_markdown(summary: dict[str, Any]) -> str:
    counts = summary.get("counts", {})
    pipeline = summary.get("pipeline", {})
    lines = [
        "# Evolution Dashboard Summary",
        "",
        f"- Window limit: {summary.get('window_limit')}",
        f"- Latest proposal: {summary.get('latest', {}).get('proposal_id')}",
        f"- Latest action: {summary.get('latest', {}).get('action_id')}",
        "",
        "## Counts",
        "",
    ]
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Pipeline", ""]
    for k, v in pipeline.items():
        lines.append(f"- {k}: {v}")
    for title, key in [
        ("Proposal status", "proposal_status"),
        ("Proposal risk", "proposal_risk"),
        ("Proposal subjects", "proposal_subjects"),
        ("Action types", "action_types"),
        ("Guard status", "guard_status"),
    ]:
        lines += ["", f"## {title}", ""]
        for name, value in _top_items(summary.get(key, {}), limit=10):
            lines.append(f"- {name}: {value}")
    return "\n".join(lines).strip() + "\n"


def render_html(summary: dict[str, Any]) -> str:
    def lis(mapping: dict[str, Any]) -> str:
        return (
            "".join(
                f"<li><strong>{html.escape(str(k))}</strong>: {html.escape(str(v))}</li>"
                for k, v in _top_items(mapping, 10)
            )
            or "<li>None</li>"
        )

    def metric_card(title: str, value: Any, hint: str = "", tone: str = "default") -> str:
        tone_cls = {
            "default": "",
            "good": " good",
            "warn": " warn",
            "bad": " bad",
        }.get(tone, "")
        return (
            f'<div class="metric-card{tone_cls}">' 
            f'<div class="metric-title">{html.escape(str(title))}</div>'
            f'<div class="metric-value">{html.escape(str(value))}</div>'
            f'<div class="metric-hint">{html.escape(str(hint))}</div>'
            f'</div>'
        )

    counts = lis(summary.get("counts", {}))
    pipeline = summary.get("pipeline", {}) or {}
    proposal_status = lis(summary.get("proposal_status", {}))
    proposal_risk = lis(summary.get("proposal_risk", {}))
    proposal_subjects = lis(summary.get("proposal_subjects", {}))
    action_types = lis(summary.get("action_types", {}))
    action_actors = lis(summary.get("action_actors", {}))
    guard_status = lis(summary.get("guard_status", {}))
    baseline_regressions = lis(summary.get("baseline_regressions", {}))
    latest = summary.get("latest", {}) or {}
    schedule = summary.get("schedule_overview", {}) or {}

    guard_pass_rate = float(pipeline.get("guard_pass_rate", 0.0) or 0.0)
    regression_rate = float(pipeline.get("regression_rate", 0.0) or 0.0)
    pending_approval = pipeline.get("pending_approval", 0)
    actionable = pipeline.get("actionable", 0)

    recommendations = []
    if regression_rate > 0:
        recommendations.append("Investigate baseline regressions before approving or applying new proposals.")
    if pending_approval:
        recommendations.append("Review pending proposals and verify guard/baseline evidence before approval.")
    if actionable:
        recommendations.append("Actionable proposals exist — check risk level and subject hotspots.")
    if not recommendations:
        recommendations.append("Pipeline looks stable. Continue normal review cadence and keep evidence retained.")

    recommendation_html = "".join(f"<li>{html.escape(x)}</li>" for x in recommendations)

    latest_html = "".join(
        f"<li><strong>{html.escape(str(k))}</strong>: {html.escape(str(v))}</li>"
        for k, v in latest.items()
    ) or "<li>None</li>"
    schedule_html = "".join(
        f"<li><strong>{html.escape(str(k))}</strong>: {html.escape(str(v))}</li>"
        for k, v in schedule.items()
    ) or "<li>None</li>"

    metrics = "".join([
        metric_card("Pending approval", pending_approval, "Proposals waiting for reviewer / approver action", "warn" if pending_approval else "good"),
        metric_card("Actionable", actionable, "Items that can move forward after review", "warn" if actionable else "default"),
        metric_card("Guard pass rate", f"{guard_pass_rate:.1%}", "Share of recent guards that passed", "good" if guard_pass_rate >= 0.8 else "warn"),
        metric_card("Regression rate", f"{regression_rate:.1%}", "Recent baseline compares with detected regression", "bad" if regression_rate > 0 else "good"),
    ])

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Evolution Dashboard Summary</title>
<style>
:root{{--bg:#f6f8fb;--card:#fff;--border:#d8dee9;--text:#17212b;--muted:#5f6b7a;--accent:#2f6feb;--good:#1a7f37;--warn:#9a6700;--bad:#cf222e;}}
body{{font-family:Arial,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:24px;line-height:1.5}}
h1,h2,h3{{margin:0 0 10px 0}}p{{margin:0}}.hero{{background:linear-gradient(135deg,#ffffff,#eef4ff);border:1px solid var(--border);border-radius:16px;padding:18px 20px;margin-bottom:18px;box-shadow:0 8px 24px rgba(15,23,42,.06)}}
.badges{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}}.badge{{background:#eaf2ff;color:#1f4b99;border:1px solid #c7dbff;border-radius:999px;padding:4px 10px;font-size:12px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:14px;margin-bottom:18px}}.metric-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;box-shadow:0 4px 14px rgba(15,23,42,.04)}}.metric-card.good{{border-color:#b7dfc2;background:#f2fbf5}}.metric-card.warn{{border-color:#f0d8a8;background:#fff9ec}}.metric-card.bad{{border-color:#f1b7bb;background:#fff4f5}}
.metric-title{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}.metric-value{{font-size:28px;font-weight:700;margin-top:6px}}.metric-hint{{font-size:12px;color:var(--muted);margin-top:8px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(320px,1fr));gap:16px}}.card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;box-shadow:0 4px 14px rgba(15,23,42,.04)}}.wide{{grid-column:1 / -1}}
ul{{margin:0;padding-left:20px}}li{{margin:4px 0}}.section-note{{font-size:13px;color:var(--muted);margin-bottom:10px}}.footer{{margin-top:18px;font-size:12px;color:var(--muted)}}
@media (max-width: 960px){{.kpi-grid{{grid-template-columns:repeat(2,minmax(160px,1fr))}}.grid{{grid-template-columns:1fr}}}}
</style>
</head><body>
<div class="hero">
  <h1>Evolution Dashboard Summary</h1>
  <p>Operator-facing summary for the self-evolution pipeline: inspection → plan → proposal → guard → baseline → approval / rollback.</p>
  <div class="badges">
    <span class="badge">Window limit: {html.escape(str(summary.get('window_limit')))}</span>
    <span class="badge">Latest proposal: {html.escape(str(latest.get('proposal_id')))}</span>
    <span class="badge">Latest action: {html.escape(str(latest.get('action_id')))}</span>
    <span class="badge">Latest schedule: {html.escape(str(latest.get('schedule_cycle_id')))}</span>
  </div>
</div>
<div class="kpi-grid">{metrics}</div>
<div class="grid">
  <div class="card"><h2>Counts</h2><div class="section-note">High-level object counts across the evolution subsystem.</div><ul>{counts}</ul></div>
  <div class="card"><h2>Pipeline summary</h2><div class="section-note">Operational health signals for review throughput and regression pressure.</div><ul>{lis(pipeline)}</ul></div>
  <div class="card"><h2>Proposal status</h2><div class="section-note">Current distribution of proposals by governance state.</div><ul>{proposal_status}</ul></div>
  <div class="card"><h2>Proposal risk</h2><div class="section-note">Risk distribution — use this to separate low-risk automation from human review.</div><ul>{proposal_risk}</ul></div>
  <div class="card"><h2>Subject hotspots</h2><div class="section-note">Recurring subjects that may indicate unstable modules or recurring operational pain.</div><ul>{proposal_subjects}</ul></div>
  <div class="card"><h2>Guard and baseline</h2><div class="section-note">Guard outcomes and regression signals should be checked before approval or apply.</div><h3>Guard status</h3><ul>{guard_status}</ul><h3 style="margin-top:12px">Baseline regressions</h3><ul>{baseline_regressions}</ul></div>
  <div class="card"><h2>Governance activity</h2><div class="section-note">Recent approval / reject / apply / rollback activity.</div><h3>Action types</h3><ul>{action_types}</ul><h3 style="margin-top:12px">Action actors</h3><ul>{action_actors}</ul></div>
  <div class="card"><h2>Latest objects</h2><div class="section-note">Quick drill-down identifiers for recent evidence.</div><ul>{latest_html}</ul></div>
  <div class="card wide"><h2>Scheduler overview</h2><div class="section-note">Recent auto-scheduler cycle hints for proposal generation and automation pacing.</div><ul>{schedule_html}</ul></div>
  <div class="card wide"><h2>Recommended operator actions</h2><div class="section-note">Start here when the dashboard looks abnormal or when preparing a review window.</div><ul>{recommendation_html}</ul></div>
</div>
<div class="footer">Generated by ArcHillx evolution dashboard exporter. Keep the JSON summary for automation and the HTML / Markdown bundle for human review.</div>
</body></html>"""


def write_dashboard_bundle(summary: dict[str, Any]) -> dict[str, str]:
    stamp = _now_stamp()
    base = _dashboard_dir() / f"evolution_summary_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    html_path = base.with_suffix(".html")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    html_path.write_text(render_html(summary), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}
