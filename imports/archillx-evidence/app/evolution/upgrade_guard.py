from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .proposal_store import latest_json, load_json, write_json
from .schemas import EvolutionGuardCheck, EvolutionGuardRun, EvolutionProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class _CmdResult:
    ok: bool
    output: str


class UpgradeGuard:
    def _run_cmd(self, cmd: list[str], timeout: int = 900) -> _CmdResult:
        proc = subprocess.run(
            cmd,
            cwd=str(_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or '').strip()
        if len(out) > 3000:
            out = out[-3000:]
        return _CmdResult(ok=(proc.returncode == 0), output=out)

    def _check(self, name: str, cmd: list[str], timeout: int = 900) -> EvolutionGuardCheck:
        res = self._run_cmd(cmd, timeout=timeout)
        return EvolutionGuardCheck(
            name=name,
            status='passed' if res.ok else 'failed',
            detail=res.output or ('ok' if res.ok else 'failed'),
            command=' '.join(cmd),
        )

    def _load_proposal(self, proposal_id: str | None = None) -> EvolutionProposal:
        payload = load_json('proposals', proposal_id) if proposal_id else latest_json('proposals')
        if payload is None:
            raise ValueError('No evolution proposal available for guard execution.')
        return EvolutionProposal.model_validate(payload)

    def run(self, proposal_id: str | None = None, mode: str = 'quick') -> EvolutionGuardRun:
        proposal = self._load_proposal(proposal_id)
        checks: list[EvolutionGuardCheck] = []
        checks.append(self._check('compileall', [sys.executable, '-m', 'compileall', 'app', 'scripts', 'tests']))
        pytest_targets = ['tests/test_evolution_routes.py', 'tests/test_evolution_proposals.py'] if mode == 'quick' else ['tests']
        checks.append(self._check('pytest', [sys.executable, '-m', 'pytest', '-q', *pytest_targets], timeout=1200))
        smoke_script = 'scripts/smoke_test_v46_proposals.py'
        checks.append(self._check('smoke', [sys.executable, smoke_script], timeout=900))
        checks.append(self._check('release_check', [sys.executable, 'scripts/release_check.py', '--mode', 'ci', '--skip-compile', '--skip-pytest', '--json'], timeout=1200))
        checks.append(self._check('rollback_check', [sys.executable, 'scripts/rollback_check.py', '--mode', 'ci', '--skip-compile', '--skip-pytest', '--skip-shellcheck', '--skip-migration-check', '--skip-migration-history', '--skip-backup-verify', '--skip-restore-drill', '--json'], timeout=1200))
        checks.append(self._check('migration_check', [sys.executable, 'scripts/check_migration_state.py', '.env.prod'], timeout=300))
        status = 'passed' if all(c.status == 'passed' for c in checks) else 'failed'
        guard = EvolutionGuardRun(
            guard_id=f"guard_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
            created_at=_now_iso(),
            proposal_id=proposal.proposal_id,
            mode='full' if mode == 'full' else 'quick',
            status=status,
            checks=checks,
        )
        path = write_json('guards', guard.guard_id, guard.model_dump(mode='json'))
        guard.evidence_path = path
        return guard
