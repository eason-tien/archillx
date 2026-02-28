import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

html = (ROOT / "app/ui/static/index.html").read_text(encoding="utf-8")
js = (ROOT / "app/ui/static/app.js").read_text(encoding="utf-8")
assert 'btn-open-evolution-final' in html
assert 'btn-open-evolution-summary' in html
assert 'btn-open-evolution-nav' in html
assert '/v1/evolution/final' in js
assert '/v1/evolution/summary' in js
assert '/v1/evolution/nav' in js
print('OK_V81_UI_OVERVIEW_EVOLUTION_SHORTCUTS_SMOKE')
