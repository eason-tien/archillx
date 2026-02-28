from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.security.audit_store import append_jsonl, load_jsonl_records, rotate_audit_file


def test_rotate_audit_file(tmp_path):
    old_dir = settings.evidence_dir
    old_max = settings.audit_file_max_bytes
    settings.evidence_dir = str(tmp_path)
    settings.audit_file_max_bytes = 10
    try:
        append_jsonl({'k': 'x' * 40})
        result = rotate_audit_file()
        assert result['rotated'] is True
        assert Path(result['archived_to']).exists()
    finally:
        settings.evidence_dir = old_dir
        settings.audit_file_max_bytes = old_max


def test_load_jsonl_records(tmp_path):
    old_dir = settings.evidence_dir
    settings.evidence_dir = str(tmp_path)
    try:
        append_jsonl({'action': 'a', 'decision': 'APPROVED'})
        items = load_jsonl_records()
        assert len(items) == 1
        assert items[0]['action'] == 'a'
    finally:
        settings.evidence_dir = old_dir
