from pathlib import Path


def test_overview_has_evolution_html_preview_buttons():
    html = Path("app/ui/static/index.html").read_text(encoding="utf-8")
    assert 'btn-open-evolution-portal-preview' in html
    assert 'btn-open-evolution-final-preview' in html
    assert 'Open portal HTML' in html
    assert 'Open final HTML' in html


def test_app_js_wires_html_preview_buttons():
    js = Path("app/ui/static/app.js").read_text(encoding="utf-8")
    assert "/v1/evolution/portal/preview" in js
    assert "/v1/evolution/final/preview" in js
    assert 'btn-open-evolution-portal-preview' in js
    assert 'btn-open-evolution-final-preview' in js
