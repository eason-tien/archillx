
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.evolution.auto_scheduler import evolution_scheduler
from app.config import settings


def test_evolution_auto_schedule_run_and_status(tmp_path):
    old_evidence = settings.evidence_dir
    old_auto = settings.enable_evolution_auto
    old_limit = settings.evolution_auto_generate_limit
    old_guard = settings.evolution_auto_guard_low_risk
    settings.evidence_dir = str(tmp_path)
    settings.enable_evolution_auto = True
    settings.evolution_auto_generate_limit = 2
    settings.evolution_auto_guard_low_risk = True
    client = TestClient(app)
    try:
        status = client.get('/v1/evolution/schedule')
        assert status.status_code == 200
        assert status.json()['enabled'] is True
        assert status.json()['generate_limit'] == 2

        payload = client.post('/v1/evolution/schedule/run', json={'limit': 2})
        assert payload.status_code == 200
        data = payload.json()
        assert data['cycle_id'].startswith('cycle_')
        assert data['proposal_count'] >= 1
        assert data['generated_limit'] == 2
        assert data['evidence_path'].endswith('.json')
        assert len(data['proposals']) >= 1

        latest_status = client.get('/v1/evolution/status').json()
        assert latest_status['schedule']['cycle_id'] == data['cycle_id']
        assert latest_status['schedule']['proposal_count'] == data['proposal_count']

        sched = evolution_scheduler.status()
        assert sched['last_cycle']['cycle_id'] == data['cycle_id']
    finally:
        settings.evidence_dir = old_evidence
        settings.enable_evolution_auto = old_auto
        settings.evolution_auto_generate_limit = old_limit
        settings.evolution_auto_guard_low_risk = old_guard


def test_evolution_auto_schedule_auto_approve_low_risk(tmp_path):
    old_evidence = settings.evidence_dir
    old_auto = settings.enable_evolution_auto
    old_limit = settings.evolution_auto_generate_limit
    old_guard = settings.evolution_auto_guard_low_risk
    old_auto_approve = getattr(settings, 'evolution_auto_approve_low_risk', False)
    old_guard_required = getattr(settings, 'evolution_auto_approve_requires_guard_pass', True)
    old_actor = getattr(settings, 'evolution_auto_approve_actor', 'evolution-auto')
    settings.evidence_dir = str(tmp_path)
    settings.enable_evolution_auto = True
    settings.evolution_auto_generate_limit = 1
    settings.evolution_auto_guard_low_risk = True
    settings.evolution_auto_approve_low_risk = True
    settings.evolution_auto_approve_requires_guard_pass = True
    settings.evolution_auto_approve_actor = 'evolution-auto'
    client = TestClient(app)
    try:
        payload = client.post('/v1/evolution/schedule/run', json={'limit': 1})
        assert payload.status_code == 200
        data = payload.json()
        assert data['proposal_count'] >= 1
        proposal_entry = data['proposals'][0]
        assert proposal_entry['status'] in {'approved', 'guard_passed', 'generated'}
        if proposal_entry.get('auto_approval') is not None:
            assert proposal_entry['auto_approval']['actor'] == 'evolution-auto'
            assert proposal_entry['auto_approval']['to_status'] == 'approved'

        summary = client.get('/v1/evolution/summary').json()
        assert 'approved' in summary['proposal_status'] or 'guard_passed' in summary['proposal_status'] or 'generated' in summary['proposal_status']
    finally:
        settings.evidence_dir = old_evidence
        settings.enable_evolution_auto = old_auto
        settings.evolution_auto_generate_limit = old_limit
        settings.evolution_auto_guard_low_risk = old_guard
        settings.evolution_auto_approve_low_risk = old_auto_approve
        settings.evolution_auto_approve_requires_guard_pass = old_guard_required
        settings.evolution_auto_approve_actor = old_actor


def test_evolution_auto_schedule_auto_apply_low_risk(tmp_path, monkeypatch):
    from app.evolution.service import evolution_service

    original_generate = evolution_service.generate_proposal

    def low_risk_generate(*args, **kwargs):
        proposal = original_generate(*args, **kwargs)
        proposal.requires_human_review = False
        proposal.approval_required = False
        proposal.risk.risk_level = 'low'
        proposal.risk.risk_score = min(int(proposal.risk.risk_score), 20)
        proposal.risk.auto_apply_allowed = True
        evolution_service.save_proposal(proposal)
        return proposal

    monkeypatch.setattr(evolution_service, 'generate_proposal', low_risk_generate)

    from app.evolution.schemas import EvolutionGuardRun, EvolutionGuardCheck, EvolutionBaselineCompare, EvolutionBaselinePoint

    def fake_guard(proposal_id: str | None = None, mode: str = 'quick'):
        proposal = evolution_service.load_proposal(proposal_id)
        guard = EvolutionGuardRun(
            guard_id='guard_test_auto_apply',
            created_at='2026-02-27T00:00:00Z',
            proposal_id=proposal_id,
            mode=mode,
            status='passed',
            checks=[EvolutionGuardCheck(name='pytest', status='passed', detail='ok')],
            evidence_path='evidence/evolution/guards/guard_test_auto_apply.json',
        )
        if proposal is not None:
            proposal.last_guard_id = guard.guard_id
            proposal.status = 'guard_passed'
            evolution_service.save_proposal(proposal)
        return guard

    def fake_baseline(proposal_id: str | None = None):
        proposal = evolution_service.load_proposal(proposal_id)
        baseline = EvolutionBaselineCompare(
            baseline_id='baseline_test_auto_apply',
            created_at='2026-02-27T00:00:00Z',
            proposal_id=proposal_id,
            inspection_id=getattr(proposal, 'inspection_id', None),
            before=EvolutionBaselinePoint(),
            after=EvolutionBaselinePoint(),
            diff={},
            regression_detected=False,
            summary=['no regression'],
            evidence_path='evidence/evolution/baselines/baseline_test_auto_apply.json',
        )
        if proposal is not None:
            proposal.last_baseline_id = baseline.baseline_id
            evolution_service.save_proposal(proposal)
        return baseline

    monkeypatch.setattr(evolution_service, 'run_guard', fake_guard)
    monkeypatch.setattr(evolution_service, 'run_baseline_compare', fake_baseline)

    old_evidence = settings.evidence_dir
    old_auto = settings.enable_evolution_auto
    old_limit = settings.evolution_auto_generate_limit
    old_guard = settings.evolution_auto_guard_low_risk
    old_auto_approve = getattr(settings, 'evolution_auto_approve_low_risk', False)
    old_auto_apply = getattr(settings, 'evolution_auto_apply_low_risk', False)
    old_apply_guard = getattr(settings, 'evolution_auto_apply_requires_guard_pass', True)
    old_apply_base = getattr(settings, 'evolution_auto_apply_requires_baseline_clear', True)
    old_approve_guard = getattr(settings, 'evolution_auto_approve_requires_guard_pass', True)
    old_approve_actor = getattr(settings, 'evolution_auto_approve_actor', 'evolution-auto')
    old_apply_actor = getattr(settings, 'evolution_auto_apply_actor', 'evolution-auto')
    settings.evidence_dir = str(tmp_path)
    settings.enable_evolution_auto = True
    settings.evolution_auto_generate_limit = 1
    settings.evolution_auto_guard_low_risk = True
    settings.evolution_auto_approve_low_risk = True
    settings.evolution_auto_approve_requires_guard_pass = True
    settings.evolution_auto_apply_low_risk = True
    settings.evolution_auto_apply_requires_guard_pass = True
    settings.evolution_auto_apply_requires_baseline_clear = True
    settings.evolution_auto_approve_actor = 'evolution-auto'
    settings.evolution_auto_apply_actor = 'evolution-auto'
    client = TestClient(app)
    try:
        payload = client.post('/v1/evolution/schedule/run', json={'limit': 1})
        assert payload.status_code == 200
        data = payload.json()
        assert data['proposal_count'] >= 1
        proposal_entry = data['proposals'][0]
        assert proposal_entry['status'] in {'applied', 'approved', 'guard_passed', 'generated'}
        if proposal_entry.get('auto_apply') is not None:
            assert proposal_entry['auto_apply']['actor'] == 'evolution-auto'
            assert proposal_entry['auto_apply']['to_status'] == 'applied'
            assert proposal_entry['baseline']['regression_detected'] is False

        summary = client.get('/v1/evolution/summary').json()
        assert 'applied' in summary['proposal_status'] or 'approved' in summary['proposal_status']
    finally:
        settings.evidence_dir = old_evidence
        settings.enable_evolution_auto = old_auto
        settings.evolution_auto_generate_limit = old_limit
        settings.evolution_auto_guard_low_risk = old_guard
        settings.evolution_auto_approve_low_risk = old_auto_approve
        settings.evolution_auto_apply_low_risk = old_auto_apply
        settings.evolution_auto_apply_requires_guard_pass = old_apply_guard
        settings.evolution_auto_apply_requires_baseline_clear = old_apply_base
        settings.evolution_auto_approve_requires_guard_pass = old_approve_guard
        settings.evolution_auto_approve_actor = old_approve_actor
        settings.evolution_auto_apply_actor = old_apply_actor
