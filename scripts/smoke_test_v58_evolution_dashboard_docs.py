from pathlib import Path

root = Path(__file__).resolve().parents[1]
doc = root / "docs" / "EVOLUTION_DASHBOARD.md"
assert doc.exists(), "missing docs/EVOLUTION_DASHBOARD.md"
text = doc.read_text(encoding="utf-8")
for needle in ["GET /v1/evolution/summary", "POST /v1/evolution/dashboard/render", "pipeline", "proposal_risk", "schedule_overview"]:
    assert needle in text, f"missing {needle}"
for rel in ["README.md", "DEPLOYMENT.md", "docs/EVOLUTION_DESIGN.md", "docs/EVOLUTION_RUNBOOK.md", "docs/OPERATIONS_RUNBOOK.md", "docs/EVOLUTION_GOVERNANCE.md"]:
    t = (root / rel).read_text(encoding="utf-8")
    assert "docs/EVOLUTION_DASHBOARD.md" in t
print("OK_V58_EVOLUTION_DASHBOARD_DOCS_SMOKE")
