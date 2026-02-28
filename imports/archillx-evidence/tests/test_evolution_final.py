from fastapi.testclient import TestClient

from app.main import app


def test_evolution_final_bundle_and_render(client: TestClient):
    r = client.get('/v1/evolution/final')
    assert r.status_code == 200
    body = r.json()
    assert 'primary_routes' in body
    assert '/v1/evolution/final' in body['primary_routes']
    assert 'docs' in body

    r2 = client.post('/v1/evolution/final/render')
    assert r2.status_code == 200
    payload = r2.json()
    assert 'bundle' in payload and 'paths' in payload
    assert payload['paths']['json'].endswith('.json')
    assert payload['paths']['markdown'].endswith('.md')
    assert payload['paths']['html'].endswith('.html')
