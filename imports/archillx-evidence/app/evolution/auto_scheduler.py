
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from ..config import settings
from .proposal_store import latest_json, write_json
from .schemas import EvolutionProposal
from .service import evolution_service

logger = logging.getLogger("archillx.evolution.scheduler")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvolutionAutoScheduler:
    def __init__(self) -> None:
        self._scheduler = None
        self._started = False
        self._last_cycle: dict | None = None

    def startup(self) -> None:
        if self._started or not getattr(settings, 'enable_evolution', True) or not getattr(settings, 'enable_evolution_auto', False):
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            self._scheduler = BackgroundScheduler(timezone=settings.cron_timezone)
            self._scheduler.start()
            expr = str(getattr(settings, 'evolution_auto_cycle_cron', '15 */6 * * *')).strip()
            parts = expr.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid evolution auto cycle cron: {expr!r}")
            trig = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4], timezone=settings.cron_timezone)
            self._scheduler.add_job(self.run_cycle, trigger=trig, id='evolution_auto_cycle', name='evolution_auto_cycle', replace_existing=True, misfire_grace_time=120)
            self._started = True
            logger.info('evolution auto scheduler started (cron=%s)', expr)
        except ImportError:
            logger.warning('apscheduler not installed — evolution auto scheduler disabled')
        except Exception as e:
            logger.error('evolution auto scheduler startup failed: %s', e)

    def shutdown(self) -> None:
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        self._scheduler = None
        self._started = False

    def status(self) -> dict:
        next_run = None
        if self._scheduler:
            try:
                job = self._scheduler.get_job('evolution_auto_cycle')
                if job and job.next_run_time:
                    next_run = job.next_run_time.isoformat()
            except Exception:
                next_run = None
        return {
            'enabled': bool(getattr(settings, 'enable_evolution_auto', False) and getattr(settings, 'enable_evolution', True)),
            'started': self._started,
            'cron': getattr(settings, 'evolution_auto_cycle_cron', '15 */6 * * *'),
            'generate_limit': int(getattr(settings, 'evolution_auto_generate_limit', 3)),
            'auto_guard_low_risk': bool(getattr(settings, 'evolution_auto_guard_low_risk', True)),
            'auto_approve_low_risk': bool(getattr(settings, 'evolution_auto_approve_low_risk', False)),
            'auto_approve_requires_guard_pass': bool(getattr(settings, 'evolution_auto_approve_requires_guard_pass', True)),
            'auto_apply_low_risk': bool(getattr(settings, 'evolution_auto_apply_low_risk', False)),
            'auto_apply_requires_guard_pass': bool(getattr(settings, 'evolution_auto_apply_requires_guard_pass', True)),
            'auto_apply_requires_baseline_clear': bool(getattr(settings, 'evolution_auto_apply_requires_baseline_clear', True)),
            'guard_mode': getattr(settings, 'evolution_auto_guard_mode', 'quick'),
            'auto_approve_actor': getattr(settings, 'evolution_auto_approve_actor', 'evolution-auto'),
            'auto_apply_actor': getattr(settings, 'evolution_auto_apply_actor', 'evolution-auto'),
            'next_run': next_run,
            'last_cycle': self._last_cycle,
        }

    def latest_cycle(self) -> dict | None:
        payload = latest_json('schedules')
        return payload or self._last_cycle

    def run_cycle(self, limit: int | None = None) -> dict:
        if not getattr(settings, 'enable_evolution', True):
            raise RuntimeError('Evolution module is disabled.')
        if limit is None:
            limit = max(1, int(getattr(settings, 'evolution_auto_generate_limit', 3) or 3))
        inspection = evolution_service.run_inspection()
        plan = evolution_service.build_plan(inspection)
        proposals: list[dict] = []
        generated = min(limit, len(plan.items))
        for idx in range(generated):
            proposal: EvolutionProposal = evolution_service.generate_proposal(plan=plan, item_index=idx)
            entry = {
                'proposal_id': proposal.proposal_id,
                'title': proposal.title,
                'risk_level': proposal.risk.risk_level,
                'approval_required': proposal.approval_required,
                'status': proposal.status,
                'guard': None,
            }
            auto_guard_enabled = bool(getattr(settings, 'evolution_auto_guard_low_risk', True))
            auto_approve_enabled = bool(getattr(settings, 'evolution_auto_approve_low_risk', False))
            auto_approve_requires_guard_pass = bool(getattr(settings, 'evolution_auto_approve_requires_guard_pass', True))
            auto_approve_actor = str(getattr(settings, 'evolution_auto_approve_actor', 'evolution-auto') or 'evolution-auto')
            auto_apply_enabled = bool(getattr(settings, 'evolution_auto_apply_low_risk', False))
            auto_apply_requires_guard_pass = bool(getattr(settings, 'evolution_auto_apply_requires_guard_pass', True))
            auto_apply_requires_baseline_clear = bool(getattr(settings, 'evolution_auto_apply_requires_baseline_clear', True))
            auto_apply_actor = str(getattr(settings, 'evolution_auto_apply_actor', 'evolution-auto') or 'evolution-auto')
            guard = None
            baseline = None
            if auto_guard_enabled and not proposal.approval_required and proposal.risk.auto_apply_allowed:
                guard = evolution_service.run_guard(proposal_id=proposal.proposal_id, mode=getattr(settings, 'evolution_auto_guard_mode', 'quick'))
                entry['guard'] = {'guard_id': guard.guard_id, 'status': guard.status, 'mode': guard.mode}
            refreshed = evolution_service.load_proposal(proposal.proposal_id) or proposal
            if auto_approve_enabled and not refreshed.approval_required and refreshed.risk.auto_apply_allowed:
                guard_ok = (guard is not None and guard.status == 'passed') or (not auto_approve_requires_guard_pass)
                if refreshed.status in {'generated', 'guard_passed'} and guard_ok:
                    approved, action = evolution_service.approve_proposal(
                        refreshed.proposal_id,
                        actor=auto_approve_actor,
                        reason='auto-approved low-risk proposal by scheduler',
                    )
                    refreshed = approved
                    entry['auto_approval'] = {
                        'action_id': action.action_id,
                        'actor': action.actor,
                        'from_status': action.from_status,
                        'to_status': action.to_status,
                    }
            if auto_apply_enabled and refreshed is not None and refreshed.risk.auto_apply_allowed and not refreshed.approval_required:
                guard_ok = (guard is not None and guard.status == 'passed') or (not auto_apply_requires_guard_pass)
                if refreshed.status == 'approved' and guard_ok:
                    baseline = evolution_service.run_baseline_compare(proposal_id=refreshed.proposal_id)
                    entry['baseline'] = {
                        'baseline_id': baseline.baseline_id,
                        'regression_detected': baseline.regression_detected,
                    }
                    baseline_ok = (not baseline.regression_detected) or (not auto_apply_requires_baseline_clear)
                    if baseline_ok:
                        applied, action = evolution_service.apply_proposal(
                            refreshed.proposal_id,
                            actor=auto_apply_actor,
                            reason='auto-applied low-risk proposal by scheduler after guard/baseline checks',
                        )
                        refreshed = applied
                        entry['auto_apply'] = {
                            'action_id': action.action_id,
                            'actor': action.actor,
                            'from_status': action.from_status,
                            'to_status': action.to_status,
                        }
            if refreshed is not None:
                entry['status'] = refreshed.status
            proposals.append(entry)
        payload = {
            'cycle_id': f"cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            'created_at': _now_iso(),
            'inspection_id': inspection.inspection_id,
            'plan_id': plan.plan_id,
            'proposal_count': len(proposals),
            'generated_limit': limit,
            'auto_guard_low_risk': bool(getattr(settings, 'evolution_auto_guard_low_risk', True)),
            'auto_approve_low_risk': bool(getattr(settings, 'evolution_auto_approve_low_risk', False)),
            'auto_approve_requires_guard_pass': bool(getattr(settings, 'evolution_auto_approve_requires_guard_pass', True)),
            'auto_apply_low_risk': bool(getattr(settings, 'evolution_auto_apply_low_risk', False)),
            'auto_apply_requires_guard_pass': bool(getattr(settings, 'evolution_auto_apply_requires_guard_pass', True)),
            'auto_apply_requires_baseline_clear': bool(getattr(settings, 'evolution_auto_apply_requires_baseline_clear', True)),
            'guard_mode': getattr(settings, 'evolution_auto_guard_mode', 'quick'),
            'auto_approve_actor': getattr(settings, 'evolution_auto_approve_actor', 'evolution-auto'),
            'auto_apply_actor': getattr(settings, 'evolution_auto_apply_actor', 'evolution-auto'),
            'proposals': proposals,
        }
        payload['evidence_path'] = write_json('schedules', payload['cycle_id'], payload)
        self._last_cycle = payload
        return payload


evolution_scheduler = EvolutionAutoScheduler()
