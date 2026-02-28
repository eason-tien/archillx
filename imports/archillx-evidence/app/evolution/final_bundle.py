from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .proposal_store import write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_final_bundle(payload: dict) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"evolution_final_{ts}_{uuid4().hex[:8]}"
    json_path = write_json("dashboards", base, payload)

    summary = payload.get("summary", {})
    latest = summary.get("latest", {}) if isinstance(summary, dict) else {}
    md_lines = [
        "# Evolution Final Bundle",
        "",
        f"Generated at: {payload.get('generated_at')}",
        "",
        "## Overview",
        f"- Status: **{payload.get('status', 'ready')}**",
        f"- Scope: {payload.get('scope', 'evolution subsystem final overview')}",
        "",
        "## Latest Objects",
    ]
    for k, v in latest.items():
        md_lines.append(f"- {k}: `{v}`")
    md_lines.extend([
        "",
        "## Primary APIs",
    ])
    for route in payload.get('primary_routes', []):
        md_lines.append(f"- `{route}`")
    md_lines.extend([
        "",
        "## Documents",
    ])
    for doc in payload.get('docs', []):
        if isinstance(doc, dict):
            md_lines.append(f"- {doc.get('name')}: `{doc.get('path')}`")
        else:
            md_lines.append(f"- `{doc}`")
    md_lines.extend([
        "",
        "## Evidence",
        f"- Base dir: `{payload.get('evidence_base_dir')}`",
        f"- Total indexed items: {payload.get('evidence_total_items')}",
        "",
        "## Recommended Flows",
    ])
    for flow in payload.get('recommended_flows', []):
        md_lines.append(f"- **{flow.get('label')}**: {flow.get('target')}")
    md_path = json_path.replace('.json', '.md')
    Path(md_path).write_text("\n".join(md_lines) + "\n", encoding='utf-8')

    docs_html = ''.join(f"<li><b>{d.get('name')}</b>: <code>{d.get('path')}</code></li>" for d in payload.get('docs', []) if isinstance(d, dict))
    routes_html = ''.join(f"<li><code>{r}</code></li>" for r in payload.get('primary_routes', []))
    flows_html = ''.join(f"<li><b>{f.get('label')}</b>: {f.get('target')}</li>" for f in payload.get('recommended_flows', []))
    latest_html = ''.join(f"<li><b>{k}</b>: <code>{v}</code></li>" for k, v in latest.items())
    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Evolution Final Bundle</title>
<style>body{{font-family:Arial,sans-serif;margin:24px;color:#1f2937;background:#fafafa}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}} .card{{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.04)}} .hero{{margin-bottom:18px}} code{{background:#f3f4f6;padding:2px 6px;border-radius:6px}}</style>
</head><body>
<div class='hero'><h1>Evolution Final Bundle</h1><p><b>Status:</b> {payload.get('status', 'ready')} &nbsp; <b>Generated:</b> {payload.get('generated_at')}</p></div>
<div class='grid'>
<div class='card'><h3>Latest Objects</h3><ul>{latest_html}</ul></div>
<div class='card'><h3>Primary APIs</h3><ul>{routes_html}</ul></div>
<div class='card'><h3>Documents</h3><ul>{docs_html}</ul></div>
<div class='card'><h3>Recommended Flows</h3><ul>{flows_html}</ul></div>
</div>
<p><b>Evidence base:</b> <code>{payload.get('evidence_base_dir')}</code> &nbsp; <b>Total items:</b> {payload.get('evidence_total_items')}</p>
</body></html>"""
    html_path = json_path.replace('.json', '.html')
    Path(html_path).write_text(html, encoding='utf-8')
    return {"json": json_path, "markdown": md_path, "html": html_path}
