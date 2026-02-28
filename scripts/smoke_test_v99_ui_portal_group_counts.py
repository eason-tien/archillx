from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

js = (ROOT / "app/ui/static/app.js").read_text()
css = (ROOT / "app/ui/static/styles.css").read_text()
assert "apiCount" in js
assert "htmlCount" in js
assert "group-count" in js
assert ".group-count" in css
print("OK_V99_UI_PORTAL_GROUP_COUNTS_SMOKE")
