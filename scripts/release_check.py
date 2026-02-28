#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def run_cmd(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as e:
        return False, f'exception: {e}'
    output = (proc.stdout or '').strip()
    if len(output) > 4000:
        output = output[-4000:]
    return proc.returncode == 0, output


def add(results: list[CheckResult], name: str, ok: bool, severity: str, detail: str, command: Optional[str] = None):
    results.append(CheckResult(name=name, ok=ok, severity=severity, detail=detail, command=command))


def main() -> int:
    ap = argparse.ArgumentParser(description='ArcHillx release gate checks')
    ap.add_argument('--mode', choices=['ci', 'deploy', 'full'], default='full')
    ap.add_argument('--env-file', default='.env.prod')
    ap.add_argument('--skip-pytest', action='store_true')
    ap.add_argument('--skip-compile', action='store_true')
    ap.add_argument('--skip-preflight', action='store_true')
    ap.add_argument('--skip-compose', action='store_true')
    ap.add_argument('--skip-sandbox-check', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    env_file = ROOT / args.env_file
    env_map = load_env_file(env_file)
    results: list[CheckResult] = []

    required_paths = [
        ROOT / 'docker-compose.prod.yml',
        ROOT / 'scripts' / 'preflight_deploy.sh',
        ROOT / 'scripts' / 'migrate.sh',
        ROOT / 'scripts' / 'check_migration_state.py',
        ROOT / 'docs' / 'METRICS_DASHBOARD.md',
        ROOT / 'docs' / 'TELEMETRY_API.md',
    ]
    for p in required_paths:
        add(results, f'path:{p.relative_to(ROOT)}', p.exists(), 'error', 'exists' if p.exists() else 'missing')

    if not args.skip_compile:
        cmd = [sys.executable, '-m', 'compileall', 'app', 'scripts', 'tests', 'alembic']
        ok, out = run_cmd(cmd)
        add(results, 'compileall', ok, 'error', out or ('ok' if ok else 'compile failed'), ' '.join(shlex.quote(x) for x in cmd))

    if not args.skip_pytest:
        cmd = [sys.executable, '-m', 'pytest', 'tests', '-q']
        ok, out = run_cmd(cmd, timeout=1200)
        add(results, 'pytest', ok, 'error', out or ('ok' if ok else 'pytest failed'), ' '.join(shlex.quote(x) for x in cmd))

    if args.mode in {'deploy', 'full'}:
        add(results, f'env:{args.env_file}', env_file.exists(), 'error', 'exists' if env_file.exists() else 'missing')
        if env_file.exists():
            required_env = ['API_KEY', 'ADMIN_TOKEN', 'DB_PASSWORD', 'MYSQL_ROOT_PASSWORD']
            missing = [k for k in required_env if not env_map.get(k)]
            add(results, 'env:required_keys', not missing, 'error', 'ok' if not missing else f'missing: {", ".join(missing)}')

        if not args.skip_compose:
            ok_docker, out_docker = run_cmd(['docker', 'compose', 'version'])
            add(results, 'docker_compose_available', ok_docker, 'error', out_docker or ('ok' if ok_docker else 'docker compose unavailable'), 'docker compose version')
            if ok_docker:
                ok_cfg, out_cfg = run_cmd(['docker', 'compose', '-f', 'docker-compose.prod.yml', 'config'])
                add(results, 'docker_compose_config', ok_cfg, 'error', out_cfg or ('ok' if ok_cfg else 'compose config invalid'), 'docker compose -f docker-compose.prod.yml config')

        if not args.skip_preflight and (ROOT / 'scripts' / 'preflight_deploy.sh').exists():
            ok, out = run_cmd(['bash', './scripts/preflight_deploy.sh'], timeout=900)
            add(results, 'preflight_deploy', ok, 'error', out or ('ok' if ok else 'preflight failed'), 'bash ./scripts/preflight_deploy.sh')

        if not args.skip_sandbox_check:
            code_exec_enabled = (env_map.get('ARCHILLX_ENABLE_CODE_EXEC', 'false').lower() == 'true')
            backend = env_map.get('ARCHILLX_SANDBOX_BACKEND', 'process').lower()
            if code_exec_enabled and backend == 'docker':
                image = env_map.get('ARCHILLX_SANDBOX_DOCKER_IMAGE', 'archillx-sandbox:latest')
                ok, out = run_cmd(['docker', 'image', 'inspect', image])
                add(results, 'sandbox_image_present', ok, 'error', out or ('ok' if ok else f'image missing: {image}'), f'docker image inspect {shlex.quote(image)}')
            else:
                add(results, 'sandbox_image_present', True, 'info', 'skipped (code_exec disabled or non-docker backend)')

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
    out_path = EVIDENCE_DIR / f'release_check_{stamp}.json'
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    report['evidence'] = str(out_path.relative_to(ROOT))

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"release_check passed={report['passed']} evidence={report['evidence']}")
        for item in results:
            tag = 'OK' if item.ok else ('WARN' if item.severity != 'error' else 'ERR')
            print(f'[{tag}] {item.name}: {item.detail}')

    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
