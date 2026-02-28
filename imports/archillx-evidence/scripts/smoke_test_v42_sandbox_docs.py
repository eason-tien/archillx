from pathlib import Path

required_files = [
    Path('docs/SANDBOX_HOST_ENABLEMENT.md'),
    Path('deploy/docker/seccomp/archillx-seccomp.json'),
    Path('deploy/apparmor/archillx-sandbox.profile'),
]
for f in required_files:
    assert f.exists(), f"missing required file: {f}"

doc = Path('docs/SANDBOX_HOST_ENABLEMENT.md').read_text(encoding='utf-8')
for token in [
    'ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE',
    'ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE',
    'ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE',
    'ARCHILLX_SANDBOX_REQUIRE_READ_ONLY_ROOTFS',
    'rootless',
    'preflight_deploy.sh',
    '/v1/ready',
    '/v1/telemetry',
    '/v1/audit/summary',
]:
    assert token in doc, f'missing token in sandbox doc: {token}'

readme = Path('README.md').read_text(encoding='utf-8')
assert 'docs/SANDBOX_HOST_ENABLEMENT.md' in readme

deploy = Path('DEPLOYMENT.md').read_text(encoding='utf-8')
assert 'docs/SANDBOX_HOST_ENABLEMENT.md' in deploy

runbook = Path('docs/OPERATIONS_RUNBOOK.md').read_text(encoding='utf-8')
assert 'Sandbox host enablement runbook (v42)' in runbook

print('OK_V42_SANDBOX_DOCS_SMOKE')
