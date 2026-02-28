from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

html = (ROOT / 'app/ui/static/index.html').read_text(encoding='utf-8')
js = (ROOT / 'app/ui/static/app.js').read_text(encoding='utf-8')
css = (ROOT / 'app/ui/static/styles.css').read_text(encoding='utf-8')
assert 'overview-portal-cards' in html
assert 'portal-status-badge' in js
assert 'Last updated' in js
assert '.portal-status-badge.good' in css
print('OK_V94_UI_PORTAL_STATUS_SMOKE')
