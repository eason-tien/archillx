from pathlib import Path

required = [
    'VERSION',
    'CHANGELOG.md',
    'RELEASE_NOTES_v0.44.0.md',
    'DELIVERY_MANIFEST.md',
    'FINAL_RELEASE_CHECKLIST.md',
]
for p in required:
    assert Path(p).exists(), f'missing {p}'
assert Path('VERSION').read_text(encoding='utf-8').strip() == '1.0.0'
print('OK_V44_RELEASE_BUNDLE_SMOKE')
