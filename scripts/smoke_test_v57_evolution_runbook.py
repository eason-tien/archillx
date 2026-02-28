from pathlib import Path

base = Path(__file__).resolve().parents[1]
required = [
    base / "docs/EVOLUTION_RUNBOOK.md",
    base / "docs/EVOLUTION_GOVERNANCE.md",
    base / "docs/OPERATIONS_RUNBOOK.md",
    base / "README.md",
    base / "DEPLOYMENT.md",
]
for p in required:
    assert p.exists(), f"missing: {p}"

runbook = (base / "docs/EVOLUTION_RUNBOOK.md").read_text()
assert "inspection" in runbook
assert "baseline" in runbook
assert "approve" in runbook
assert "rollback" in runbook
assert "auto-scheduler" in runbook

readme = (base / "README.md").read_text()
assert "docs/EVOLUTION_RUNBOOK.md" in readme

print("OK_V57_EVOLUTION_RUNBOOK_SMOKE")
