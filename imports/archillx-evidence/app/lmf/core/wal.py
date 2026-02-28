"""
ArcHillx LMF — Write-Ahead Log (WAL)
====================================
Standalone port from MGIS.  All MGIS store references removed.
Uses local file-based append-only JSONL log with cross-platform file locking.
"""
import json
import os
import uuid
from typing import List, Optional, Dict, Any

from ..models.wal import WALRecord
from ..models.common import MemoryStatus
from .file_utils import file_lock


class WALManager:
    def __init__(self, storage_path: str = "wal.jsonl"):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self):
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w") as f:
                pass

    def _append_record(self, record: WALRecord):
        with open(self.storage_path, "r+b") as f:
            with file_lock(f):
                # Seek to end to append
                f.seek(0, 2)
                f.write((record.model_dump_json() + "\n").encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())

    def log_start(
        self,
        task_id: str,
        item_type: str,
        payload: Dict[str, Any],
        evidence_hashes: List[str],
    ) -> str:
        from .hasher import canonicalize_and_hash

        wal_id = str(uuid.uuid4())

        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = canonicalize_and_hash(payload_str)

        record = WALRecord(
            wal_id=wal_id,
            task_id=task_id,
            item_type=item_type,
            payload=payload,
            payload_hash=payload_hash,
            evidence_hashes=evidence_hashes or [],
            status=MemoryStatus.PENDING,
        )
        self._append_record(record)
        return wal_id

    def log_commit(self, wal_id: str, store_result: str):
        # DEPRECATED: This method is dead code and should not be used.
        raise DeprecationWarning("Use log_commit_with_payload() instead")

    def log_commit_with_payload(
        self,
        wal_id: str,
        store_result: str,
        original_payload: Dict[str, Any],
        task_id: str,
        item_type: str,
        evidence_hashes: List[str],
    ):
        """
        Append-only commit without reading back the file.
        Requires passing original data to reconstruct the record.
        """
        from .hasher import canonicalize_and_hash

        payload_str = json.dumps(original_payload, sort_keys=True, default=str)
        payload_hash = canonicalize_and_hash(payload_str)

        record = WALRecord(
            wal_id=wal_id,
            task_id=task_id,
            item_type=item_type,
            payload=original_payload,
            payload_hash=payload_hash,
            evidence_hashes=evidence_hashes,
            status=MemoryStatus.COMMITTED,
            store_result=store_result,
        )
        self._append_record(record)

    def log_rollback(self, wal_id: str):
        records = self.get_all_records()
        original = next((r for r in records if r.wal_id == wal_id), None)
        if original:
            original.status = MemoryStatus.ROLLED_BACK
            self._append_record(original)

    def get_all_records(self) -> List[WALRecord]:
        records_map = {}
        if not os.path.exists(self.storage_path):
            return []

        with open(self.storage_path, "r") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rec = WALRecord(**data)
                    records_map[rec.wal_id] = rec
                except Exception as e:
                    print(
                        f"WAL Warning: Malformed record at line {line_num + 1}. "
                        f"Possible crash residue. Error: {e}"
                    )
                    raise RuntimeError(
                        f"WAL Corruption detected at line {line_num + 1}: {str(e)}"
                    )

        return list(records_map.values())
