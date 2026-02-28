from fastapi.testclient import TestClient

from app.main import app


def test_ui_contains_integrated_review_card_sections():
    client = TestClient(app)
    r = client.get('/ui')
    assert r.status_code == 200
    text = r.text
    assert 'Integrated review card' in text
    assert 'proposal-review-summary' in text
    assert 'proposal-guard-summary' in text
    assert 'proposal-baseline-summary' in text


def test_ui_js_wires_navigation_and_review_rendering():
    client = TestClient(app)
    r = client.get('/ui/static/app.js')
    assert r.status_code == 200
    js = r.text
    assert '/v1/evolution/evidence/nav/proposals/${id}' in js
    assert 'renderIntegratedReview' in js
    assert "$('#proposal-guard-summary')" in js
    assert "$('#proposal-baseline-summary')" in js
