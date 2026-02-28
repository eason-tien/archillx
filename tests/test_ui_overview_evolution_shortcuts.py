from pathlib import Path


def test_overview_contains_evolution_shortcut_buttons():
    html = Path("app/ui/static/index.html").read_text(encoding="utf-8")
    assert 'btn-open-evolution-final' in html
    assert 'btn-open-evolution-summary' in html
    assert 'btn-open-evolution-nav' in html


def test_overview_js_loads_evolution_shortcuts():
    js = Path("app/ui/static/app.js").read_text(encoding="utf-8")
    assert "/v1/evolution/final" in js
    assert "/v1/evolution/summary" in js
    assert "/v1/evolution/nav" in js
