from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

html = (ROOT / 'app/ui/static/index.html').read_text()
js = (ROOT / 'app/ui/static/app.js').read_text()
css = (ROOT / 'app/ui/static/styles.css').read_text()

checks = [
    'timeline-filter-status' in html,
    'timeline-filter-area' in html,
    'timeline-expand-all' in html,
    'timeline-collapse-all' in html,
    'wireTimelineControls' in js,
    'timeline-group-toggle' in js,
    'No timeline entries match the current filters.' in js,
    '.timeline-group' in css,
    '.timeline-group.collapsed .timeline-list' in css,
]

if not all(checks):
    raise SystemExit('v106 timeline grouping smoke failed')

print('OK_V106_TIMELINE_GROUPS_SMOKE')
