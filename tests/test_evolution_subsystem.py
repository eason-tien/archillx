
from fastapi.testclient import TestClient
from app.main import app
from app.evolution.service import evolution_service

client = TestClient(app)


def test_evolution_subsystem_manifest_and_render():
    res = client.get('/v1/evolution/subsystem')
    assert res.status_code == 200
    body = res.json()
    assert body['name'] == 'evolution'
    assert '/v1/evolution/summary' in body['api_endpoints']
    assert 'inspection' in body['capabilities']

    res2 = client.post('/v1/evolution/subsystem/render')
    assert res2.status_code == 200
    body2 = res2.json()
    assert 'manifest' in body2
    assert 'paths' in body2
    assert body2['paths']['json'].endswith('.json')
    assert body2['paths']['html'].endswith('.html')
