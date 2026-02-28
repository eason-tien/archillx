from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version_file = ROOT / "alembic" / "versions" / "20260227_000001_initial_schema.py"
text = version_file.read_text(encoding="utf-8")
assert version_file.exists(), "initial alembic revision missing"
assert 'revision = "20260227_000001"' in text
assert 'down_revision = None' in text
assert 'Base.metadata.create_all' in text
assert 'Base.metadata.drop_all' in text
print("OK_V25_MIGRATION_SMOKE")
