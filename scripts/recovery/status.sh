#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json, tempfile
from pathlib import Path
base = Path(tempfile.gettempdir())
for name in ["archillx_heartbeat.json", "archillx_recovery_state.json", "archillx_handoff.json", "archillx_recovery.lock.json"]:
    p = base / name
    print(f"[{name}] exists={p.exists()} path={p}")
    if p.exists():
        try:
            print(json.dumps(json.loads(p.read_text(encoding='utf-8')), ensure_ascii=False, indent=2))
        except Exception:
            print(p.read_text(encoding='utf-8')[:500])
PY
