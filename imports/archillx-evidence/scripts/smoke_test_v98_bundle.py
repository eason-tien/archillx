from pathlib import Path
print('OK_V98_BUNDLE_SMOKE' if all([
    Path('deploy/alertmanager/examples/fastapi_consumer.py').exists(),
    Path('deploy/alertmanager/examples/flask_consumer.py').exists(),
    'groupForKey' in Path('app/ui/static/app.js').read_text(),
    'group-count' in Path('app/ui/static/styles.css').read_text() or 'group-count' in Path('app/ui/static/app.js').read_text(),
]) else 'FAIL_V98_BUNDLE_SMOKE')
