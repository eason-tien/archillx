from pathlib import Path


def test_review_export_buttons_present():
    html = Path('app/ui/static/index.html').read_text(encoding='utf-8')
    assert 'btn-export-review-all' in html
    assert 'btn-export-review-guard' in html
    assert 'btn-export-review-baseline' in html
    assert 'btn-export-review-artifacts' in html


def test_review_export_js_hook_present():
    js = Path('app/ui/static/app.js').read_text(encoding='utf-8')
    assert 'function exportReview(section)' in js
    assert '/review/export?section=' in js
    assert 'btn-export-review-guard' in js
