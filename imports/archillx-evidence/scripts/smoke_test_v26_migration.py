from pathlib import Path


root = Path(__file__).resolve().parents[1]
migration = root / "alembic" / "versions" / "20260227_000001_initial_schema.py"
text = migration.read_text(encoding="utf-8")

assert "op.create_table(" in text, "fine-grained upgrade not found"
assert "op.drop_table(" in text, "fine-grained downgrade not found"
assert "metadata.create_all" not in text, "coarse-grained create_all still present"
assert "metadata.drop_all" not in text, "coarse-grained drop_all still present"

print("OK_V26_FINE_GRAINED_MIGRATION_SMOKE")
