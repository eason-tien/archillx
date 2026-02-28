from __future__ import annotations

from pathlib import Path
import py_compile

root = Path(__file__).resolve().parents[1]

files = [
    root / "deploy/alertmanager/examples/test_fastapi_consumer_example.py",
    root / "deploy/alertmanager/examples/test_flask_consumer_example.py",
    root / "docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md",
]

for path in files:
    assert path.exists(), f"missing: {path}"

py_compile.compile(str(files[0]), doraise=True)
py_compile.compile(str(files[1]), doraise=True)

doc = files[2].read_text(encoding="utf-8")
assert "## Example tests" in doc
assert "test_fastapi_consumer_example.py" in doc
assert "test_flask_consumer_example.py" in doc

print("OK_V104_ALERT_CONSUMER_EXAMPLES_SMOKE")
