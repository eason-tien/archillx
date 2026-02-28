from pathlib import Path


def test_overview_template_contains_timeline_filter_controls():
    html = Path('app/ui/static/index.html').read_text()
    assert 'timeline-filter-status' in html
    assert 'timeline-filter-area' in html
    assert 'timeline-expand-all' in html
    assert 'timeline-collapse-all' in html


def test_timeline_js_includes_group_toggle_and_filters():
    js = Path('app/ui/static/app.js').read_text()
    assert 'wireTimelineControls' in js
    assert 'timeline-group-toggle' in js
    assert 'No timeline entries match the current filters.' in js
    assert "window.__overviewContext" in js


def test_timeline_css_includes_group_layout_and_collapsed_state():
    css = Path('app/ui/static/styles.css').read_text()
    assert '.timeline-group' in css
    assert '.timeline-group.collapsed .timeline-list' in css
    assert '.timeline-group-badge.good' in css
    assert '.timeline-list li.good' in css
