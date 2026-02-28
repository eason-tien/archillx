from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evolution.service import evolution_service


def main():
    out = evolution_service.render_portal_bundle(limit=10)
    html_path = Path(out["paths"]["html"])
    text = html_path.read_text(encoding="utf-8")
    required = [
        "Overview & quick actions",
        "Operations lane",
        "Review & approval lane",
        "Evidence lane",
        "Dashboard lane",
        "Runbook lane",
    ]
    for token in required:
        assert token in text, token
    print("OK_V66_EVOLUTION_PORTAL_HOME_SMOKE")


if __name__ == "__main__":
    main()
