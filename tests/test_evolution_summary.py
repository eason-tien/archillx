from fastapi.testclient import TestClient

from app.main import app


def test_evolution_summary_api(monkeypatch):
    client = TestClient(app)

    data = {
        'inspections': [
            {'inspection_id': 'insp2', 'created_at': '2026-02-27T00:00:02Z', 'status': 'critical', 'findings': [], 'signal_snapshot': {'created_at': 'x','readiness': {}, 'migration': {}, 'telemetry': {}, 'audit_summary': {}, 'gate_summary': {}}, 'evidence_path': '/tmp/insp2.json'},
            {'inspection_id': 'insp1', 'created_at': '2026-02-27T00:00:01Z', 'status': 'ok', 'findings': [], 'signal_snapshot': {'created_at': 'x','readiness': {}, 'migration': {}, 'telemetry': {}, 'audit_summary': {}, 'gate_summary': {}}, 'evidence_path': '/tmp/insp1.json'},
        ],
        'plans': [
            {'plan_id': 'plan1', 'created_at': '2026-02-27T00:00:03Z', 'inspection_id': 'insp2', 'items': [], 'evidence_path': '/tmp/plan1.json'},
        ],
        'proposals': [
            {
                'proposal_id': 'prop1', 'created_at': '2026-02-27T00:00:04Z', 'plan_id': 'plan1', 'inspection_id': 'insp2', 'source_subject': 'sandbox',
                'title': 'Tighten sandbox', 'summary': '...', 'suggested_changes': [], 'tests_to_add': [], 'rollout_notes': [],
                'requires_human_review': True, 'risk': {'risk_score': 82, 'risk_level': 'high', 'factors': ['sandbox'], 'auto_apply_allowed': False},
                'status': 'approved', 'approval_required': True, 'approved_by': 'alice', 'approved_at': '2026-02-27T00:00:05Z',
                'rejected_by': None, 'applied_by': None, 'rolled_back_by': None, 'rejected_at': None, 'applied_at': None, 'rolled_back_at': None,
                'last_guard_id': 'guard1', 'last_baseline_id': 'base1', 'evidence_path': '/tmp/prop1.json'
            },
            {
                'proposal_id': 'prop2', 'created_at': '2026-02-27T00:00:06Z', 'plan_id': 'plan1', 'inspection_id': 'insp2', 'source_subject': 'telemetry',
                'title': 'Refine metrics', 'summary': '...', 'suggested_changes': [], 'tests_to_add': ['tests/x.py'], 'rollout_notes': [],
                'requires_human_review': False, 'risk': {'risk_score': 18, 'risk_level': 'low', 'factors': ['tested'], 'auto_apply_allowed': True},
                'status': 'guard_passed', 'approval_required': False, 'approved_by': None, 'approved_at': None,
                'rejected_by': None, 'applied_by': None, 'rolled_back_by': None, 'rejected_at': None, 'applied_at': None, 'rolled_back_at': None,
                'last_guard_id': 'guard2', 'last_baseline_id': None, 'evidence_path': '/tmp/prop2.json'
            },
        ],
        'guards': [
            {'guard_id': 'guard2', 'created_at': '2026-02-27T00:00:07Z', 'proposal_id': 'prop2', 'mode': 'quick', 'status': 'passed', 'checks': [], 'evidence_path': '/tmp/guard2.json'},
            {'guard_id': 'guard1', 'created_at': '2026-02-27T00:00:08Z', 'proposal_id': 'prop1', 'mode': 'full', 'status': 'failed', 'checks': [], 'evidence_path': '/tmp/guard1.json'},
        ],
        'baselines': [
            {'baseline_id': 'base1', 'created_at': '2026-02-27T00:00:09Z', 'proposal_id': 'prop1', 'inspection_id': 'insp2',
             'before': {'readiness_status': 'ok', 'migration_status': 'head', 'http_5xx_total': 1, 'skill_failure_total': 1, 'sandbox_blocked_total': 1, 'governor_blocked_total': 0, 'release_failed_total': 0, 'rollback_failed_total': 0},
             'after': {'readiness_status': 'ok', 'migration_status': 'head', 'http_5xx_total': 0, 'skill_failure_total': 0, 'sandbox_blocked_total': 0, 'governor_blocked_total': 0, 'release_failed_total': 0, 'rollback_failed_total': 0},
             'diff': {'http_5xx_total': -1}, 'regression_detected': False, 'summary': ['better'], 'evidence_path': '/tmp/base1.json'},
        ],
        'actions': [
            {'action_id': 'act1', 'created_at': '2026-02-27T00:00:10Z', 'proposal_id': 'prop1', 'action': 'approve', 'actor': 'alice', 'reason': None, 'from_status': 'guard_passed', 'to_status': 'approved', 'evidence_path': '/tmp/act1.json'},
            {'action_id': 'act2', 'created_at': '2026-02-27T00:00:11Z', 'proposal_id': 'prop1', 'action': 'apply', 'actor': 'alice', 'reason': None, 'from_status': 'approved', 'to_status': 'applied', 'evidence_path': '/tmp/act2.json'},
        ],
        'schedules': [
            {'cycle_id': 'cycle1', 'proposal_count': 2, 'generated_limit': 3, 'created_at': '2026-02-27T00:00:12Z'}
        ],
    }

    monkeypatch.setattr('app.evolution.service.list_json', lambda kind, limit=20: data.get(kind, [])[:limit])

    r = client.get('/v1/evolution/summary', params={'limit': 20})
    assert r.status_code == 200
    body = r.json()
    assert body['window_limit'] == 20
    assert body['counts']['proposals'] == 2
    assert body['proposal_status']['approved'] == 1
    assert body['proposal_status']['guard_passed'] == 1
    assert body['proposal_risk']['high'] == 1
    assert body['proposal_subjects']['sandbox'] == 1
    assert body['action_types']['approve'] == 1
    assert body['guard_status']['passed'] == 1
    assert body['pipeline']['pending_approval'] == 0
    assert body['pipeline']['auto_apply_candidates'] == 1
    assert body['pipeline']['guard_pass_rate'] == 0.5
    assert body['pipeline']['regression_rate'] == 0.0
    assert body['latest']['proposal_id'] == 'prop1'
    assert body['schedule_overview']['latest_cycle_id'] == 'cycle1'
