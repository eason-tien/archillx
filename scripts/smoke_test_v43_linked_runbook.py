from pathlib import Path

root = Path(__file__).resolve().parents[1]
req = [
    root / "docs" / "RELEASE_ROLLBACK_RESTORE_RUNBOOK.md",
    root / "docs" / "OPERATIONS_RUNBOOK.md",
    root / "DEPLOYMENT.md",
    root / "README.md",
]
for p in req:
    assert p.exists(), f"missing {p}"

linked = (root / "docs" / "RELEASE_ROLLBACK_RESTORE_RUNBOOK.md").read_text()
assert "release_check.sh" in linked
assert "rollback_check.sh" in linked
assert "restore_drill.sh" in linked
assert "gate_summary.sh" in linked

ops = (root / "docs" / "OPERATIONS_RUNBOOK.md").read_text()
assert "RELEASE_ROLLBACK_RESTORE_RUNBOOK.md" in ops

print("OK_V43_LINKED_RUNBOOK_SMOKE")
