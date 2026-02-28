from __future__ import annotations

from types import SimpleNamespace



def test_agent_run_success(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    def fake_run(loop_input):
        assert loop_input.command == 'search docs'
        assert loop_input.session_id == 42
        return SimpleNamespace(
            success=True,
            task_id=101,
            skill_used='web_search',
            model_used='provider/model-x',
            output={'answer': 'ok'},
            tokens_used=123,
            elapsed_s=0.42,
            governor_approved=True,
            error=None,
            memory_hits=[{'id': 1, 'content': 'doc'}],
        )

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post('/v1/agent/run', json={'command': 'search docs', 'session_id': 42})
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert body['task_id'] == 101
    assert body['skill_used'] == 'web_search'
    assert body['tokens_used'] == 123
    assert body['memory_hits'][0]['id'] == 1


def test_agent_run_invalid_input(client, monkeypatch):
    from app.loop import main_loop as loop_mod

    def fake_run(_loop_input):
        raise ValueError('budget not allowed')

    monkeypatch.setattr(loop_mod.main_loop, 'run', fake_run)
    resp = client.post('/v1/agent/run', json={'command': 'run', 'budget': 'wrong'})
    assert resp.status_code == 400
    detail = resp.json()['detail']
    assert detail['code'] == 'AGENT_RUN_INVALID'



def test_memory_add_passes_payload(client, monkeypatch):
    from app.memory import store as store_mod

    captured = {}

    def fake_add(content, source='user', tags=None, importance=0.5, metadata=None):
        captured.update({
            'content': content,
            'source': source,
            'tags': tags,
            'importance': importance,
            'metadata': metadata,
        })
        return 555

    monkeypatch.setattr(store_mod.memory_store, 'add', fake_add)
    resp = client.post('/v1/memory', json={
        'content': 'cron failed once',
        'source': 'system',
        'tags': ['cron', 'error'],
        'importance': 0.9,
        'metadata': {'run_id': 'r1'},
    })
    assert resp.status_code == 200
    assert resp.json()['memory_id'] == 555
    assert captured == {
        'content': 'cron failed once',
        'source': 'system',
        'tags': ['cron', 'error'],
        'importance': 0.9,
        'metadata': {'run_id': 'r1'},
    }



def test_memory_recent_limit(client, monkeypatch):
    from app.memory import store as store_mod

    def fake_recent(limit=10):
        assert limit == 3
        return [{'id': 7, 'content': 'recent memory'}]

    monkeypatch.setattr(store_mod.memory_store, 'get_recent', fake_recent)
    resp = client.get('/v1/memory/recent?limit=3')
    assert resp.status_code == 200
    body = resp.json()
    assert body['items'][0]['id'] == 7



def test_cron_list_returns_jobs(client, monkeypatch):
    from app.runtime import cron as cron_mod

    monkeypatch.setattr(
        cron_mod.cron_system,
        'list_jobs',
        lambda: [{'name': 'job-a', 'skill_name': 'web_search', 'enabled': True}],
    )
    resp = client.get('/v1/cron')
    assert resp.status_code == 200
    body = resp.json()
    assert body['jobs'][0]['name'] == 'job-a'



def test_cron_remove_calls_remove(client, monkeypatch):
    from app.runtime import cron as cron_mod

    captured = {}

    def fake_remove(name):
        captured['name'] = name

    monkeypatch.setattr(cron_mod.cron_system, 'remove', fake_remove)
    resp = client.delete('/v1/cron/job-z')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'removed', 'name': 'job-z'}
    assert captured['name'] == 'job-z'



def test_sessions_create_and_end(client, monkeypatch):
    from app.runtime.lifecycle import lifecycle

    monkeypatch.setattr(lifecycle.sessions, 'create', lambda name, context: 88)
    end_calls = {}

    def fake_end(session_id):
        end_calls['session_id'] = session_id

    monkeypatch.setattr(lifecycle.sessions, 'end', fake_end)

    create_resp = client.post('/v1/sessions', json={'name': 'night shift', 'context': {'team': 'A'}})
    assert create_resp.status_code == 200
    assert create_resp.json()['session_id'] == 88

    end_resp = client.delete('/v1/sessions/88')
    assert end_resp.status_code == 200
    assert end_resp.json() == {'status': 'ended', 'session_id': 88}
    assert end_calls['session_id'] == 88



def test_goals_create_and_update_completed(client, monkeypatch):
    from app.loop.goal_tracker import goal_tracker

    monkeypatch.setattr(goal_tracker, 'create', lambda title, description, priority, context: 321)
    monkeypatch.setattr(goal_tracker, 'get', lambda goal_id: {'id': goal_id, 'status': 'active'})
    completed = {}

    def fake_complete(goal_id):
        completed['goal_id'] = goal_id

    monkeypatch.setattr(goal_tracker, 'complete', fake_complete)

    create_resp = client.post('/v1/goals', json={'title': 'Finish audit', 'priority': 7, 'context': {'owner': 'qa'}})
    assert create_resp.status_code == 200
    assert create_resp.json()['goal_id'] == 321

    update_resp = client.patch('/v1/goals/321', json={'status': 'completed'})
    assert update_resp.status_code == 200
    assert update_resp.json()['id'] == 321
    assert completed['goal_id'] == 321
