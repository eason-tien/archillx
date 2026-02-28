from pathlib import Path

required = [
    Path('docs/EVOLUTION_GOVERNANCE.md'),
    Path('docs/EVOLUTION_DESIGN.md'),
    Path('README.md'),
    Path('DEPLOYMENT.md'),
    Path('docs/OPERATIONS_RUNBOOK.md'),
]
for p in required:
    assert p.exists(), f'missing {p}'

text = Path('docs/EVOLUTION_GOVERNANCE.md').read_text()
for phrase in [
    'Reviewer', 'Approver', 'Operator', 'guard_passed', 'approved', 'applied', 'rolled_back', '/v1/evolution/summary'
]:
    assert phrase in text, f'missing phrase: {phrase}'

readme = Path('README.md').read_text()
assert 'EVOLUTION_GOVERNANCE.md' in readme
assert 'Evolution governance guide (v54)' in Path('DEPLOYMENT.md').read_text()
assert 'Evolution governance runbook (v54)' in Path('docs/OPERATIONS_RUNBOOK.md').read_text()
print('OK_V54_EVOLUTION_GOVERNANCE_DOCS_SMOKE')
