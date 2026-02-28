#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / 'evidence' / 'releases'


@dataclass
class CheckResult:
    name: str
    ok: bool
    severity: str
    detail: str
    command: Optional[str] = None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_env_file(path: Path) -> dict:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def run_cmd(cmd: list[str], cwd: Optional[Path] = None, timeout: int = 300, env: Optional[dict[str, str]] = None) -> tuple[bool, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
            env=merged_env,
        )
    except Exception as e:
        return False, f'exception: {e}'
    out = (proc.stdout or '').strip()
    if len(out) > 4000:
        out = out[-4000:]
    return proc.returncode == 0, out


def add(results: list[CheckResult], name: str, ok: bool, severity: str, detail: str, command: Optional[str] = None) -> None:
    results.append(CheckResult(name=name, ok=ok, severity=severity, detail=detail, command=command))


def find_latest_backup(backup_dir: Path) -> Optional[Path]:
    candidates = sorted(backup_dir.glob('archillx_backup_*.tar.gz'))
    return candidates[-1] if candidates else None


def shell_syntax_check(path: Path) -> tuple[bool, str]:
    return run_cmd(['bash', '-n', str(path)])


def main() -> int:
    ap = argparse.ArgumentParser(description='ArcHillx rollback readiness gate')
    ap.add_argument('--mode', choices=['ci', 'deploy', 'full'], default='full')
    ap.add_argument('--env-file', default='.env.prod')
    ap.add_argument('--backup-archive', default='')
    ap.add_argument('--backup-dir', default='')
    ap.add_argument('--skip-pytest', action='store_true')
    ap.add_argument('--skip-compile', action='store_true')
    ap.add_argument('--skip-shellcheck', action='store_true')
    ap.add_argument('--skip-migration-check', action='store_true')
    ap.add_argument('--skip-migration-history', action='store_true')
    ap.add_argument('--skip-backup-verify', action='store_true')
    ap.add_argument('--skip-restore-drill', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    env_file = ROOT / args.env_file
    env_map = load_env_file(env_file)
    results: list[CheckResult] = []

    required_paths = [
        ROOT / 'scripts' / 'backup_stack.sh',
        ROOT / 'scripts' / 'restore_stack.sh',
        ROOT / 'scripts' / 'restore_drill.sh',
        ROOT / 'scripts' / 'verify_backup_archive.py',
        ROOT / 'scripts' / 'migrate.sh',
        ROOT / 'scripts' / 'check_migration_state.py',
        ROOT / 'deploy' / 'systemd' / 'archillx-backup.timer',
        ROOT / 'deploy' / 'systemd' / 'archillx-restore-drill.timer',
        ROOT / 'DEPLOYMENT.md',
    ]
    for p in required_paths:
        add(results, f'path:{p.relative_to(ROOT)}', p.exists(), 'error', 'exists' if p.exists() else 'missing')

    if not args.skip_compile:
        cmd = [sys.executable, '-m', 'compileall', 'app', 'scripts', 'tests', 'alembic']
        ok, out = run_cmd(cmd, timeout=900)
        add(results, 'compileall', ok, 'error', out or ('ok' if ok else 'compile failed'), ' '.join(shlex.quote(x) for x in cmd))

    if not args.skip_pytest:
        cmd = [sys.executable, '-m', 'pytest', 'tests', '-q']
        ok, out = run_cmd(cmd, timeout=1200)
        add(results, 'pytest', ok, 'error', out or ('ok' if ok else 'pytest failed'), ' '.join(shlex.quote(x) for x in cmd))

    if not args.skip_shellcheck:
        for rel in ['scripts/backup_stack.sh', 'scripts/restore_stack.sh', 'scripts/restore_drill.sh', 'scripts/preflight_deploy.sh']:
            p = ROOT / rel
            ok, out = shell_syntax_check(p)
            add(results, f'shellcheck:{rel}', ok, 'error', out or ('ok' if ok else 'shell syntax invalid'), f'bash -n {rel}')

    if args.mode in {'deploy', 'full'}:
        add(results, f'env:{args.env_file}', env_file.exists(), 'error', 'exists' if env_file.exists() else 'missing')
        backup_dir = Path(args.backup_dir) if args.backup_dir else Path(env_map.get('BACKUP_DIR') or (ROOT / 'backups'))
        backup_archive = Path(args.backup_archive) if args.backup_archive else find_latest_backup(backup_dir)
        add(results, 'backup_dir', backup_dir.exists(), 'warn', str(backup_dir))

        if not args.skip_migration_check:
            cmd = [sys.executable, 'scripts/check_migration_state.py', args.env_file]
            ok, out = run_cmd(cmd, timeout=300)
            add(results, 'migration_state', ok, 'error', out or ('ok' if ok else 'migration check failed'), ' '.join(shlex.quote(x) for x in cmd))

        if not args.skip_backup_verify:
            if backup_archive and backup_archive.exists():
                cmd = [sys.executable, 'scripts/verify_backup_archive.py', str(backup_archive), '--json']
                ok, out = run_cmd(cmd, timeout=300)
                add(results, 'backup_archive_verify', ok, 'error', out or ('ok' if ok else 'backup archive invalid'), ' '.join(shlex.quote(x) for x in cmd))
            else:
                add(results, 'backup_archive_verify', False, 'error', f'backup archive not found (searched in {backup_dir})')

        if not args.skip_restore_drill:
            if backup_archive and backup_archive.exists():
                cmd = ['bash', 'scripts/restore_drill.sh', str(backup_archive)]
                ok, out = run_cmd(cmd, timeout=600, env={'DRILL_REPORT_DIR': str(ROOT / 'evidence' / 'drills')})
                add(results, 'restore_drill_dry_run', ok, 'error', out or ('ok' if ok else 'restore drill failed'), ' '.join(shlex.quote(x) for x in cmd))
            else:
                add(results, 'restore_drill_dry_run', False, 'error', 'skipped because no backup archive was found')

        # downgrade readiness: require explicit migration file and history command to work
        if not args.skip_migration_history:
            cmd = ['bash', 'scripts/migrate.sh', 'history']
            ok, out = run_cmd(cmd, timeout=300)
            add(results, 'migration_history', ok, 'error', out or ('ok' if ok else 'unable to read migration history'), 'bash scripts/migrate.sh history')
        else:
            add(results, 'migration_history', True, 'info', 'skipped by flag')

    failures = [r for r in results if not r.ok and (args.strict or r.severity == 'error')]
    report = {
        'timestamp': utc_now(),
        'mode': args.mode,
        'strict': args.strict,
        'env_file': args.env_file,
        'passed': not failures,
        'summary': {
            'checks_total': len(results),
            'checks_failed': len([r for r in results if not r.ok]),
            'errors_failed': len([r for r in results if (not r.ok and r.severity == 'error')]),
        },
        'results': [asdict(r) for r in results],
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    out_path = EVIDENCE_DIR / f'rollback_check_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    report['evidence'] = str(out_path.relative_to(ROOT))

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"rollback_check passed={report['passed']} evidence={report['evidence']}")
        for item in results:
            tag = 'OK' if item.ok else ('WARN' if item.severity != 'error' else 'ERR')
            print(f'[{tag}] {item.name}: {item.detail}')

    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
