import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

js = (ROOT / 'app/ui/static/app.js').read_text()
css = (ROOT / 'app/ui/static/styles.css').read_text()
assert 'portalStatusMeta' in js
assert 'title="${badge.title}"' in js
assert 'Last updated at' in js
assert '.portal-status-badge.good' in css
assert '.portal-status-badge.warn' in css
assert '.portal-status-badge.bad' in css
print('OK_V97_UI_PORTAL_BADGE_HOVER_SMOKE')
