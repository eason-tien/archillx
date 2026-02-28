from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RETENTION_DAYS = 30


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path('evidence')
    root.mkdir(parents=True, exist_ok=True)
    src = root / 'entropy_engine.jsonl'
    if not src.exists():
        print('NO_SOURCE')
        return 0

    archive_dir = root / 'archives'
    archive_dir.mkdir(parents=True, exist_ok=True)
    idx_path = root / 'index.json'

    day = datetime.now(timezone.utc).strftime('%Y%m%d')
    dst = archive_dir / f'entropy_engine_{day}.jsonl'
    if dst.exists():
        # prevent overwrite
        suffix = datetime.now(timezone.utc).strftime('%H%M%S')
        dst = archive_dir / f'entropy_engine_{day}_{suffix}.jsonl'

    dst.write_bytes(src.read_bytes())
    src.write_text('', encoding='utf-8')

    lines = [ln for ln in dst.read_text(encoding='utf-8').splitlines() if ln.strip()]
    first_ts = None
    last_ts = None
    for ln in lines:
        try:
            obj = json.loads(ln)
            ts = obj.get('timestamp') or obj.get('ts')
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
        except Exception:
            continue

    rec = {
        'date': day,
        'file': str(dst),
        'sha256': sha256(dst),
        'lines': len(lines),
        'first_ts': first_ts,
        'last_ts': last_ts,
    }

    idx = []
    if idx_path.exists():
        try:
            idx = json.loads(idx_path.read_text(encoding='utf-8'))
            if not isinstance(idx, list):
                idx = []
        except Exception:
            idx = []
    idx.append(rec)
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    for f in sorted(archive_dir.glob('entropy_engine_*.jsonl')):
        try:
            ts = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if ts < cutoff:
                gz = f.with_suffix(f.suffix + '.gz')
                with f.open('rb') as fin, gzip.open(gz, 'wb') as fout:
                    fout.write(fin.read())
                f.unlink(missing_ok=True)
        except Exception:
            continue

    print(f'ROTATED={dst}')
    print(f'INDEX={idx_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
