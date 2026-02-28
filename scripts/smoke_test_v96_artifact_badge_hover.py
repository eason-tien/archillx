from pathlib import Path
js = Path('app/ui/static/app.js').read_text(encoding='utf-8')
html = Path('app/ui/static/index.html').read_text(encoding='utf-8')
assert 'Artifacts were rendered at' in js
assert 'Core patch artifacts are missing' in js
assert 'hover for details' in html
print('OK_V96_UI_ARTIFACT_BADGE_HOVER_SMOKE')
