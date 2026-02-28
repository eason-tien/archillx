from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / 'evidence' / 'dashboards'
OUTDIR.mkdir(parents=True, exist_ok=True)

DOCS = {
    'top_level': [
        'README.md', 'DEPLOYMENT.md', 'CHANGELOG.md', 'RELEASE_NOTES_v0.44.0.md',
        'DELIVERY_MANIFEST.md', 'FINAL_RELEASE_CHECKLIST.md', 'docs/SYSTEM_FINAL_DELIVERY.md', 'docs/SYSTEM_DELIVERY_INDEX.md'
    ],
    'operations': [
        'docs/OPERATIONS_RUNBOOK.md', 'docs/RELEASE_ROLLBACK_RESTORE_RUNBOOK.md', 'docs/SANDBOX_HOST_ENABLEMENT.md', 'docs/GATE_SUMMARY_DASHBOARD.md'
    ],
    'evolution': [
        'docs/EVOLUTION_SUBSYSTEM.md', 'docs/EVOLUTION_DELIVERY.md', 'docs/EVOLUTION_DELIVERY_MANIFEST.md',
        'docs/EVOLUTION_GOVERNANCE.md', 'docs/EVOLUTION_RUNBOOK.md', 'docs/EVOLUTION_DASHBOARD.md',
        'docs/EVOLUTION_NAVIGATION.md', 'docs/EVOLUTION_PORTAL.md', 'docs/EVOLUTION_FINAL.md'
    ],
    'assets': [
        'deploy/grafana/archillx-dashboard.json', '.env.example', '.env.prod.example', 'docker-compose.yml', 'docker-compose.prod.yml'
    ]
}


def build_index() -> dict:
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'version': (ROOT / 'VERSION').read_text(encoding='utf-8').strip() if (ROOT / 'VERSION').exists() else 'unknown',
        'sections': {},
        'recommended_flow': [
            'README.md', 'docs/SYSTEM_FINAL_DELIVERY.md', 'DEPLOYMENT.md', 'FINAL_RELEASE_CHECKLIST.md', 'docs/OPERATIONS_RUNBOOK.md'
        ],
    }
    for k, items in DOCS.items():
        payload['sections'][k] = [{'path': p, 'exists': (ROOT / p).exists()} for p in items]
    return payload


def render_md(payload: dict) -> str:
    lines = ['# System Delivery Portal', '', f"Generated: {payload['generated_at']}", f"Version: {payload['version']}", '']
    lines += ['## Recommended flow']
    for p in payload['recommended_flow']:
        lines.append(f'- `{p}`')
    for section, items in payload['sections'].items():
        lines += ['', f"## {section.replace('_', ' ').title()}"]
        for item in items:
            mark = 'OK' if item['exists'] else 'MISSING'
            lines.append(f"- [{mark}] `{item['path']}`")
    return '\n'.join(lines) + '\n'


def render_html(payload: dict) -> str:
    def lis(items):
        return ''.join(f"<li><code>{i['path']}</code> <span>{'OK' if i['exists'] else 'MISSING'}</span></li>" for i in items)
    cards = ''.join(f"<section><h2>{k.replace('_',' ').title()}</h2><ul>{lis(v)}</ul></section>" for k, v in payload['sections'].items())
    flow = ''.join(f'<li><code>{p}</code></li>' for p in payload['recommended_flow'])
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>System Delivery Portal</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f9; color: #222; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(300px,1fr)); gap: 16px; }}
section {{ background: #fff; border: 1px solid #ddd; border-radius: 12px; padding: 16px; }}
code {{ background: #f1f1f4; padding: 2px 6px; border-radius: 6px; }}
ul {{ padding-left: 18px; }}
span {{ color: #666; margin-left: 6px; }}
</style></head>
<body><h1>System Delivery Portal</h1><p><strong>Version:</strong> {payload['version']}<br><strong>Generated:</strong> {payload['generated_at']}</p>
<section><h2>Recommended flow</h2><ol>{flow}</ol></section><div class="grid">{cards}</div></body></html>'''


def main():
    payload = build_index()
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    json_path = OUTDIR / f'system_delivery_portal_{ts}.json'
    md_path = OUTDIR / f'system_delivery_portal_{ts}.md'
    html_path = OUTDIR / f'system_delivery_portal_{ts}.html'
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    md_path.write_text(render_md(payload), encoding='utf-8')
    html_path.write_text(render_html(payload), encoding='utf-8')
    print(f'OK_V69_SYSTEM_DELIVERY_PORTAL={json_path}')
    print(md_path)
    print(html_path)

if __name__ == '__main__':
    main()
