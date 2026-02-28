from pathlib import Path

paths = [
    Path('docs/EVOLUTION_EVIDENCE.md'),
    Path('README.md'),
]
for p in paths:
    assert p.exists(), f"missing {p}"
text = Path('docs/EVOLUTION_EVIDENCE.md').read_text(encoding='utf-8')
assert '/v1/evolution/evidence/index' in text
assert '/v1/evolution/evidence/nav/proposals/{proposal_id}' in text
print('OK_V61_EVOLUTION_EVIDENCE_DOCS_SMOKE')
