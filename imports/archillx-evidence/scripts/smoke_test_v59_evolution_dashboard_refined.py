from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evolution.service import evolution_service

result = evolution_service.render_dashboard_bundle(limit=5)
html_path = Path(result["paths"]["html"])
text = html_path.read_text(encoding="utf-8")
assert "Evolution Dashboard Summary" in text
assert "Pending approval" in text
assert "Recommended operator actions" in text
assert "Scheduler overview" in text
assert "Subject hotspots" in text
print("OK_V59_EVOLUTION_DASHBOARD_REFINED_SMOKE")
