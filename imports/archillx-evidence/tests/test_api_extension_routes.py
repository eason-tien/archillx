from __future__ import annotations

from app.config import settings


def test_agent_tasks_list_passes_limit(client, monkeypatch):
    from app.runtime.lifecycle import lifecycle

    def fake_list_recent(limit=20):
        assert limit == 7
        return [{'id': 1, 'status': 'done'}]

    monkeypatch.setattr(lifecycle.tasks, 'list_recent', fake_list_recent)
    resp = client.get('/v1/agent/tasks?limit=7')
    assert resp.status_code == 200
    assert resp.json()['tasks'][0]['id'] == 1



def test_agent_task_get_not_found(client, monkeypatch):
    from app.runtime.lifecycle import lifecycle

    monkeypatch.setattr(lifecycle.tasks, 'get', lambda task_id: None)
    resp = client.get('/v1/agent/tasks/404')
    assert resp.status_code == 404
    detail = resp.json()['detail']
    assert detail['code'] == 'TASK_NOT_FOUND'
    assert detail['details']['task_id'] == 404



def test_goals_list_active_uses_active_path(client, monkeypatch):
    from app.loop.goal_tracker import goal_tracker

    monkeypatch.setattr(goal_tracker, 'list_active', lambda: [{'id': 9, 'status': 'active'}])
    monkeypatch.setattr(goal_tracker, 'list_all', lambda: [{'id': 99, 'status': 'abandoned'}])
    resp = client.get('/v1/goals?status=active')
    assert resp.status_code == 200
    body = resp.json()
    assert body['goals'] == [{'id': 9, 'status': 'active'}]



def test_goals_delete_abandons_goal(client, monkeypatch):
    from app.loop.goal_tracker import goal_tracker

    captured = {}

    def fake_abandon(goal_id):
        captured['goal_id'] = goal_id

    monkeypatch.setattr(goal_tracker, 'abandon', fake_abandon)
    resp = client.delete('/v1/goals/33')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'abandoned', 'goal_id': 33}
    assert captured['goal_id'] == 33



def test_sessions_list_returns_active(client, monkeypatch):
    from app.runtime.lifecycle import lifecycle

    monkeypatch.setattr(lifecycle.sessions, 'list_active', lambda: [{'id': 5, 'name': 'ops'}])
    resp = client.get('/v1/sessions')
    assert resp.status_code == 200
    assert resp.json()['sessions'][0]['name'] == 'ops'



def test_lmf_disabled_returns_503(client):
    settings.enable_lmf = False
    resp = client.get('/v1/lmf/stats')
    assert resp.status_code == 503
    detail = resp.json()['detail']
    assert detail['code'] == 'LMF_DISABLED'



def test_planner_disabled_returns_503(client):
    settings.enable_planner = False
    resp = client.get('/v1/planner/plans')
    assert resp.status_code == 503
    detail = resp.json()['detail']
    assert detail['code'] == 'PLANNER_DISABLED'



def test_notifications_disabled_returns_503(client):
    settings.enable_notifications = False
    resp = client.get('/v1/notifications/status')
    assert resp.status_code == 503
    detail = resp.json()['detail']
    assert detail['code'] == 'NOTIFICATIONS_DISABLED'



def test_governor_config_reflects_settings(client):
    resp = client.get('/v1/governor/config')
    assert resp.status_code == 200
    body = resp.json()
    assert body['mode'] == settings.governor_mode
    assert 'risk_block_threshold' in body
    assert 'adaptive' in body
