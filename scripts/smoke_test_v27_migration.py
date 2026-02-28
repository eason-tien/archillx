from pathlib import Path

path = Path('alembic/versions/20260227_000001_initial_schema.py')
text = path.read_text(encoding='utf-8')
assert 'op.create_table(' in text
assert 'op.drop_table(' in text
assert 'Base.metadata' not in text
assert 'create_all' not in text
assert 'drop_all' not in text
assert 'sa.UniqueConstraint(' in text
assert text.count('op.create_table(') >= 20
print('OK_V27_EXPLICIT_MIGRATION_SMOKE')
