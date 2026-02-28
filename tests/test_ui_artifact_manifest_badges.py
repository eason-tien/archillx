from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_artifact_manifest_badges_area():
    client = TestClient(app)
    html = client.get('/ui').text
    assert 'Artifacts manifest summary' in html
    assert 'proposal-artifact-badges' in html


def test_ui_js_renders_artifact_manifest_badges():
    client = TestClient(app)
    js = client.get('/ui/static/app.js').text
    assert 'renderArtifactManifestBadges' in js
    assert 'Artifacts:' in js
    assert 'artifact_count' in js


def test_badge_color_semantics_present():
    text = Path('app/ui/static/app.js').read_text(encoding='utf-8')
    assert 'Manifest: complete' in text
    assert 'Manifest: partial' in text
    assert 'Manifest: incomplete' in text
    assert 'Bundle:' in text
    assert 'rich' in text
    assert 'minimal' in text
    css = Path('app/ui/static/styles.css').read_text(encoding='utf-8')
    assert '.artifact-badge.status-good' in css
    assert '.artifact-badge.status-warn' in css
    assert '.artifact-badge.status-bad' in css
    assert '.artifact-badge.status-neutral' in css


def test_badge_hover_details_present():
    text = Path('app/ui/static/app.js').read_text(encoding='utf-8')
    assert 'Artifacts were rendered at' in text
    assert 'Core patch artifacts are missing' in text
    html = Path('app/ui/static/index.html').read_text(encoding='utf-8')
    assert 'hover for details' in html
