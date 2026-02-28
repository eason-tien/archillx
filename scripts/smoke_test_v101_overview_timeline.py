from pathlib import Path

base = Path(__file__).resolve().parents[1]
html = (base / "app/ui/static/index.html").read_text()
js = (base / "app/ui/static/app.js").read_text()
assert "Recent evidence timeline" in html
assert "renderOverviewEvidenceTimeline" in js
assert "timeline-list" in (base / "app/ui/static/styles.css").read_text()
print("OK_V101_OVERVIEW_TIMELINE_SMOKE")
