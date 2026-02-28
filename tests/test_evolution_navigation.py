from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_evolution_navigation_and_render():
    res = client.get('/v1/evolution/nav')
    assert res.status_code == 200
    body = res.json()
    assert '/v1/evolution/summary' in body['routes']
    assert 'docs' in body
    assert 'latest' in body

    res2 = client.post('/v1/evolution/nav/render')
    assert res2.status_code == 200
    body2 = res2.json()
    assert 'navigation' in body2
    assert body2['paths']['html'].endswith('.html')
    assert body2['paths']['markdown'].endswith('.md')
    assert body2['paths']['json'].endswith('.json')
