from pathlib import Path


def test_overview_has_portal_card_grid():
    html = Path("app/ui/static/index.html").read_text()
    assert 'overview-portal-cards' in html
    assert 'Gate / portal quick links' in html


def test_app_wires_portal_cards_to_existing_buttons():
    js = Path("app/ui/static/app.js").read_text()
    assert 'renderOverviewPortalCards' in js
    assert 'btn-open-gate-portal' in js
    assert 'btn-open-restore-preview' in js
    assert 'btn-open-evolution-portal' in js
    assert 'btn-open-evolution-final' in js
    assert 'btn-open-evolution-summary' in js
    assert 'btn-open-evolution-nav' in js


def test_portal_cards_include_status_badge_and_last_updated():
    js = Path("app/ui/static/app.js").read_text()
    css = Path("app/ui/static/styles.css").read_text()
    assert 'portal-status-badge' in js
    assert 'Last updated' in js
    assert '.portal-status-badge.good' in css
    assert '.portal-card-meta' in css


def test_portal_cards_include_hover_titles_and_status_meta():
    js = Path("app/ui/static/app.js").read_text()
    assert 'portalStatusMeta' in js
    assert 'Healthy / ready.' in js
    assert 'Last updated at' in js
    assert 'title="${badge.title}"' in js


def test_portal_cards_include_api_html_group_counts():
    js = Path("app/ui/static/app.js").read_text()
    css = Path("app/ui/static/styles.css").read_text()
    assert 'apiCount' in js
    assert 'htmlCount' in js
    assert 'group-count' in js
    assert '.group-count' in css


def test_overview_template_contains_evidence_timeline_panel():
    from pathlib import Path
    html = Path("app/ui/static/index.html").read_text()
    js = Path("app/ui/static/app.js").read_text()
    assert "Recent evidence timeline" in html
    assert "renderOverviewEvidenceTimeline" in js
