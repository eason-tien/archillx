#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / 'evidence' / 'releases'
OUT_DIR = ROOT / 'evidence' / 'dashboards'


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _load_reports(kind: str, limit: int) -> list[dict[str, Any]]:
    files = sorted(EVIDENCE_DIR.glob(f'{kind}_check_*.json'))[-limit:]
    rows: list[dict[str, Any]] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        data['_path'] = str(path.relative_to(ROOT))
        rows.append(data)
    return rows


def _summarize(report: dict[str, Any], gate: str) -> dict[str, Any]:
    results = report.get('results', []) or []
    failed = [r for r in results if not r.get('ok')]
    errors = [r for r in failed if r.get('severity') == 'error']
    warnings = [r for r in failed if r.get('severity') != 'error']
    top_failed = [
        {
            'name': r.get('name'),
            'severity': r.get('severity'),
            'detail': r.get('detail', '')[:240],
        }
        for r in failed[:8]
    ]
    return {
        'gate': gate,
        'timestamp': report.get('timestamp'),
        'mode': report.get('mode'),
        'passed': bool(report.get('passed')),
        'checks_total': int(report.get('summary', {}).get('checks_total', len(results))),
        'checks_failed': int(report.get('summary', {}).get('checks_failed', len(failed))),
        'errors_failed': int(report.get('summary', {}).get('errors_failed', len(errors))),
        'warnings_failed': len(warnings),
        'evidence': report.get('evidence') or report.get('_path'),
        'top_failed': top_failed,
    }


def _history(rows: list[dict[str, Any]], gate: str) -> list[dict[str, Any]]:
    out = []
    for item in rows:
        out.append(_summarize(item, gate))
    return out


def _aggregate(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {
            'runs': 0,
            'passed': 0,
            'failed': 0,
            'pass_rate': 0.0,
            'most_common_failures': [],
            'latest_passed': None,
            'latest_failed': None,
        }
    passed = sum(1 for h in history if h['passed'])
    failed = len(history) - passed
    failure_names = Counter()
    latest_passed = None
    latest_failed = None
    for h in history:
        if h['passed'] and latest_passed is None:
            latest_passed = h['timestamp']
        if (not h['passed']) and latest_failed is None:
            latest_failed = h['timestamp']
        for item in h.get('top_failed', []):
            name = item.get('name')
            if name:
                failure_names[name] += 1
    return {
        'runs': len(history),
        'passed': passed,
        'failed': failed,
        'pass_rate': round((passed / len(history)) * 100, 2),
        'most_common_failures': [{'name': k, 'count': v} for k, v in failure_names.most_common(10)],
        'latest_passed': latest_passed,
        'latest_failed': latest_failed,
    }


def _render_markdown(data: dict[str, Any]) -> str:
    release = data['release']
    rollback = data['rollback']
    lines = [
        '# ArcHillx Gate Summary',
        '',
        f"Generated: {data['generated_at']}",
        '',
        '## Overview',
        '',
        '| Gate | Runs | Passed | Failed | Pass rate | Latest passed | Latest failed |',
        '| --- | ---: | ---: | ---: | ---: | --- | --- |',
        f"| Release | {release['aggregate']['runs']} | {release['aggregate']['passed']} | {release['aggregate']['failed']} | {release['aggregate']['pass_rate']}% | {release['aggregate']['latest_passed'] or '-'} | {release['aggregate']['latest_failed'] or '-'} |",
        f"| Rollback | {rollback['aggregate']['runs']} | {rollback['aggregate']['passed']} | {rollback['aggregate']['failed']} | {rollback['aggregate']['pass_rate']}% | {rollback['aggregate']['latest_passed'] or '-'} | {rollback['aggregate']['latest_failed'] or '-'} |",
        '',
        '## Most Common Failures',
        '',
    ]
    for gate_name, gate in [('Release', release), ('Rollback', rollback)]:
        lines.extend([f'### {gate_name}', ''])
        common = gate['aggregate']['most_common_failures']
        if not common:
            lines.append('- No failures recorded in the selected window.')
        else:
            for item in common:
                lines.append(f"- **{item['name']}** — {item['count']} times")
        lines.append('')

    lines.extend(['## Latest Runs', ''])
    for gate_name, gate in [('Release', release), ('Rollback', rollback)]:
        lines.extend([f'### {gate_name}', ''])
        if not gate['history']:
            lines.append('- No evidence files found.')
            lines.append('')
            continue
        for run in gate['history'][:5]:
            status = 'PASS' if run['passed'] else 'FAIL'
            lines.append(f"- **{status}** {run['timestamp']} · mode=`{run['mode']}` · failed={run['checks_failed']} · evidence=`{run['evidence']}`")
            for item in run.get('top_failed', [])[:3]:
                lines.append(f"  - {item['name']} ({item['severity']}): {item['detail']}")
        lines.append('')
    return '\n'.join(lines) + '\n'


def _render_html(data: dict[str, Any]) -> str:
    def cards(gate: dict[str, Any], title: str) -> str:
        agg = gate['aggregate']
        items = ''.join(
            f"<li><b>{i['name']}</b> — {i['count']} times</li>" for i in agg['most_common_failures'][:8]
        ) or '<li>No recent failures</li>'
        runs = ''.join(
            f"<tr><td>{'PASS' if r['passed'] else 'FAIL'}</td><td>{r['timestamp']}</td><td>{r['mode']}</td><td>{r['checks_failed']}</td><td><code>{r['evidence']}</code></td></tr>"
            for r in gate['history'][:6]
        ) or '<tr><td colspan="5">No evidence files found</td></tr>'
        return f"""
<section class='card'>
  <h2>{title}</h2>
  <div class='stats'>
    <div><span>Runs</span><strong>{agg['runs']}</strong></div>
    <div><span>Passed</span><strong>{agg['passed']}</strong></div>
    <div><span>Failed</span><strong>{agg['failed']}</strong></div>
    <div><span>Pass rate</span><strong>{agg['pass_rate']}%</strong></div>
  </div>
  <h3>Most common failures</h3>
  <ul>{items}</ul>
  <h3>Recent runs</h3>
  <table>
    <thead><tr><th>Status</th><th>Timestamp</th><th>Mode</th><th>Failed</th><th>Evidence</th></tr></thead>
    <tbody>{runs}</tbody>
  </table>
</section>
"""
    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>ArcHillx Gate Summary</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; background: #fafafa; }}
h1 {{ margin-bottom: 4px; }}
.muted {{ color: #666; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
.stats {{ display: grid; grid-template-columns: repeat(4, minmax(100px,1fr)); gap: 10px; margin: 12px 0 18px; }}
.stats div {{ background: #f3f4f6; border-radius: 10px; padding: 10px; }}
.stats span {{ display: block; color: #666; font-size: 12px; }}
.stats strong {{ font-size: 22px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }}
code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>ArcHillx Gate Summary</h1>
  <div class='muted'>Generated: {data['generated_at']}</div>
  <div class='grid'>
    {cards(data['release'], 'Release Gate')}
    {cards(data['rollback'], 'Rollback Gate')}
  </div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description='Generate release/rollback gate summary dashboard')
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    release_rows = list(reversed(_load_reports('release', args.limit)))
    rollback_rows = list(reversed(_load_reports('rollback', args.limit)))
    release_history = _history(release_rows, 'release')
    rollback_history = _history(rollback_rows, 'rollback')

    payload = {
        'generated_at': _utc_now(),
        'limit': args.limit,
        'release': {
            'aggregate': _aggregate(release_history),
            'history': release_history,
        },
        'rollback': {
            'aggregate': _aggregate(rollback_history),
            'history': rollback_history,
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    json_path = OUT_DIR / f'gate_summary_{stamp}.json'
    md_path = OUT_DIR / f'gate_summary_{stamp}.md'
    html_path = OUT_DIR / f'gate_summary_{stamp}.html'
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    md_path.write_text(_render_markdown(payload), encoding='utf-8')
    html_path.write_text(_render_html(payload), encoding='utf-8')

    if args.json:
        print(json.dumps({
            'ok': True,
            'json': str(json_path.relative_to(ROOT)),
            'markdown': str(md_path.relative_to(ROOT)),
            'html': str(html_path.relative_to(ROOT)),
            'release_runs': payload['release']['aggregate']['runs'],
            'rollback_runs': payload['rollback']['aggregate']['runs'],
        }, indent=2, ensure_ascii=False))
    else:
        print(f'OK_GATE_SUMMARY_JSON={json_path.relative_to(ROOT)}')
        print(f'OK_GATE_SUMMARY_MD={md_path.relative_to(ROOT)}')
        print(f'OK_GATE_SUMMARY_HTML={html_path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
