from pathlib import Path


def test_timeline_window_and_summary_cards_present():
    html = Path("app/ui/static/index.html").read_text(encoding="utf-8")
    assert 'timeline-filter-window' in html
    assert 'overview-timeline-summary' in html


def test_export_result_links_present():
    js = Path("app/ui/static/app.js").read_text(encoding="utf-8")
    assert 'function renderExportResult' in js
    assert 'export-link-row' in js
    assert "['json', data.json]" in js


def test_timeline_window_logic_present():
    js = Path("app/ui/static/app.js").read_text(encoding="utf-8")
    assert 'function withinTimelineWindow' in js
    assert 'renderTimelineSummaryCards' in js
    assert 'timeline-filter-window' in js
