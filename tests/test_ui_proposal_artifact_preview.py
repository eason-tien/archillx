from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_artifact_preview_panels():
    client = TestClient(app)
    html = client.get('/ui').text
    assert 'PR / Commit preview' in html
    assert 'Patch / Tests / Rollout preview' in html


def test_ui_js_uses_artifact_preview_endpoint():
    client = TestClient(app)
    js = client.get('/ui/static/app.js').text
    assert '/artifacts/preview' in js
    assert 'proposal-pr-preview' in js
    assert 'proposal-patch-preview' in js


def test_ui_contains_artifact_manifest_panel_and_endpoint():
    client = TestClient(app)
    html = client.get('/ui').text
    js = client.get('/ui/static/app.js').text
    assert 'Artifacts manifest summary' in html
    assert 'proposal-artifact-manifest' in html
    assert '/artifacts/manifest' in js
