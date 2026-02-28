from pathlib import Path

req = Path("docs/SYSTEM_EVOLUTION_INTEGRATION.md")
text = req.read_text()
assert "Integration overview" in text
assert "Architectural boundary" in text
assert "Deployment integration" in text
assert "Evidence integration map" in text
assert Path("README.md").read_text().find("SYSTEM_EVOLUTION_INTEGRATION.md") != -1
print("OK_V68_SYSTEM_EVOLUTION_INTEGRATION_SMOKE")
