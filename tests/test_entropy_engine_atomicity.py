from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import settings
from app.entropy.engine import EntropyEngine


def test_entropy_evidence_atomic_append_under_concurrency(tmp_path):
    old_dir = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    try:
        eng = EntropyEngine()
        vec = {'memory': 0.7, 'task': 0.7, 'model': 0.7, 'resource': 0.7, 'decision': 0.7}

        def worker(_):
            eng.evaluate_from_vector_for_test(vec, persist=True)

        with ThreadPoolExecutor(max_workers=16) as ex:
            list(ex.map(worker, range(100)))

        path = Path(tmp_path) / 'entropy_engine.jsonl'
        lines = [ln for ln in path.read_text(encoding='utf-8').splitlines() if ln.strip()]
        # includes both transition events and snapshots, must be >= 100 and all parseable
        assert len(lines) >= 100
        for ln in lines:
            obj = json.loads(ln)
            assert isinstance(obj, dict)
    finally:
        settings.evidence_dir = old_dir
