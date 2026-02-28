from pathlib import Path


def test_artifact_groups_present():
    html = Path('app/ui/static/index.html').read_text()
    js = Path('app/ui/static/app.js').read_text()
    css = Path('app/ui/static/styles.css').read_text()
    assert 'Artifacts manifest summary' in html
    assert 'groupForKey' in js
    assert 'artifact-group-head' in css
    assert 'Summary' in js and 'PR' in js and 'Patch' in js and 'Ops' in js and 'Risk' in js


def test_portal_group_counts_present():
    js = Path('app/ui/static/app.js').read_text()
    assert 'group-count' in js
    assert 'API shortcuts in this card' in js
    assert 'HTML preview shortcuts in this card' in js


def test_alert_consumer_dual_templates_present():
    doc = Path('docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md').read_text()
    fa = Path('deploy/alertmanager/examples/fastapi_consumer.py').read_text()
    fl = Path('deploy/alertmanager/examples/flask_consumer.py').read_text()
    assert '## FastAPI example' in doc
    assert '## Flask example' in doc
    assert 'FastAPI' in fa and '@app.post("/alert")' in fa
    assert 'Flask' in fl and '@app.post("/alert")' in fl
