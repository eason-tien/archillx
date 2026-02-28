from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

html = (ROOT / 'app/ui/static/index.html').read_text(encoding='utf-8')
js = (ROOT / 'app/ui/static/app.js').read_text(encoding='utf-8')
routes = (ROOT / 'app/api/evolution_routes.py').read_text(encoding='utf-8')
assert 'btn-export-review-guard' in html
assert 'btn-export-review-baseline' in html
assert 'btn-export-review-artifacts' in html
assert 'function exportReview(section)' in js
assert '/review/export?section=' in js
assert '/evolution/proposals/{proposal_id}/review/export' in routes
print('OK_V109_REVIEW_GROUP_EXPORT_SMOKE')
