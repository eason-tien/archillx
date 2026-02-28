from __future__ import annotations

import types

from app.config import settings


def test_lmf_stats_enabled_returns_store_stats(client, install_module):
    settings.enable_lmf = True
    stores_mod = types.ModuleType('app.lmf.core.stores')
    stores_mod.get_lmf_stats = lambda: {'episodic': 2, 'semantic': 1, 'working': 0}
    install_module('app.lmf.core.stores', stores_mod)

    resp = client.get('/v1/lmf/stats')
    assert resp.status_code == 200
    assert resp.json()['stats']['episodic'] == 2


def test_planner_plans_enabled_returns_plans(client, install_module):
    settings.enable_planner = True
    planner_mod = types.ModuleType('app.planner.taskgraph')
    planner_mod.task_graph_planner = types.SimpleNamespace(
        list_plans=lambda status='pending', limit=20: [
            {'id': 11, 'status': status, 'limit_seen': limit}
        ]
    )
    install_module('app.planner.taskgraph', planner_mod)

    resp = client.get('/v1/planner/plans?status=ready&limit=3')
    assert resp.status_code == 200
    body = resp.json()
    assert body['plans'][0]['id'] == 11
    assert body['plans'][0]['status'] == 'ready'
    assert body['plans'][0]['limit_seen'] == 3


def test_notifications_status_enabled_returns_backend_status(client, install_module):
    settings.enable_notifications = True
    notif_mod = types.ModuleType('app.notifications')
    notif_mod.get_notification_status = lambda: {'slack': True, 'telegram': False, 'webhook': True}
    install_module('app.notifications', notif_mod)

    resp = client.get('/v1/notifications/status')
    assert resp.status_code == 200
    body = resp.json()
    assert body['slack'] is True
    assert body['telegram'] is False


def test_proactive_projects_enabled_returns_project_list(client, install_module):
    settings.enable_proactive = True
    proactive_mod = types.ModuleType('app.autonomy.proactive')
    proactive_mod.proactive_engine = types.SimpleNamespace(
        list_projects=lambda: [{'id': 7, 'name': 'security hardening'}]
    )
    install_module('app.autonomy.proactive', proactive_mod)

    resp = client.get('/v1/proactive/projects')
    assert resp.status_code == 200
    body = resp.json()
    assert body['projects'][0]['name'] == 'security hardening'
