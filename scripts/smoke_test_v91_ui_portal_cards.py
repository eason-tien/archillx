import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

html = (ROOT / "app/ui/static/index.html").read_text()
js = (ROOT / "app/ui/static/app.js").read_text()
assert 'overview-portal-cards' in html
assert 'renderOverviewPortalCards' in js
assert 'btn-open-gate-portal' in js
assert 'btn-open-evolution-final' in js
print('OK_V91_UI_PORTAL_CARDS_SMOKE')
