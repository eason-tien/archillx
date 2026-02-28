
from pathlib import Path


def test_ui_overview_contains_integrated_system_status():
    html = Path("app/ui/static/index.html").read_text(encoding="utf-8")
    assert 'Integrated system status' in html
    assert 'system-status-cards' in html
    assert 'system-status-json' in html


def test_ui_overview_js_loads_integrated_status_endpoint():
    js = Path("app/ui/static/app.js").read_text(encoding="utf-8")
    assert "/v1/system/overview-status" in js
    assert "system-status-cards" in js
