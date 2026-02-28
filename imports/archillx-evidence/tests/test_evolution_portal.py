from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_evolution_portal_and_render():
    res = client.get('/v1/evolution/portal')
    assert res.status_code == 200
    body = res.json()
    assert 'blocks' in body
    assert 'api_entrypoints' in body['blocks']
    assert '/v1/evolution/summary' in body['blocks']['api_entrypoints']

    res2 = client.post('/v1/evolution/portal/render')
    assert res2.status_code == 200
    body2 = res2.json()
    assert 'portal' in body2
    assert body2['paths']['html'].endswith('.html')
    assert body2['paths']['markdown'].endswith('.md')
    assert body2['paths']['json'].endswith('.json')
