"""
ArcHillx v1.0.0 — Lightweight Memory Store
Keyword + importance 搜尋，不需要 vector DB 或外部依賴。
若 OLLAMA 可用則自動升級為向量搜尋（未來擴充點）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("archillx.memory")


class MemoryStore:
    """
    輕量記憶儲存：
    - 寫入 ah_memory 表
    - 以關鍵字 LIKE 搜尋 + importance 排序
    - 支援 tag 過濾
    """

    def add(self, content: str, source: str = "archillx",
            tags: list[str] | None = None,
            importance: float = 0.5,
            metadata: dict | None = None) -> int:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        m = AHMemory(
            content=content,
            source=source,
            tags=json.dumps(tags or []),
            importance=max(0.0, min(1.0, importance)),
            metadata_=json.dumps(metadata or {}),
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        logger.debug("Memory added: id=%d source=%s tags=%s", m.id, source, tags)
        return m.id

    def query(self, query: str, top_k: int = 5,
              tags: list[str] | None = None,
              min_importance: float = 0.0) -> list[dict]:
        """
        關鍵字搜尋記憶。
        回傳最多 top_k 筆，按 importance DESC 排序。
        """
        from ..db.schema import AHMemory, get_db
        db = next(get_db())

        q = db.query(AHMemory)

        # Keyword filter — split query into tokens
        tokens = [t.strip() for t in query.lower().split() if len(t.strip()) > 1]
        for tok in tokens[:4]:   # limit to first 4 tokens to avoid overly narrow results
            q = q.filter(AHMemory.content.ilike(f"%{tok}%"))

        # Importance filter
        if min_importance > 0:
            q = q.filter(AHMemory.importance >= min_importance)

        rows = q.order_by(AHMemory.importance.desc()).limit(top_k * 3).all()

        # Tag post-filter
        results = []
        for r in rows:
            if tags:
                row_tags = json.loads(r.tags or "[]")
                if not any(t in row_tags for t in tags):
                    continue
            results.append({
                "id": r.id,
                "content": r.content,
                "source": r.source,
                "tags": json.loads(r.tags or "[]"),
                "importance": r.importance,
                "metadata": json.loads(r.metadata_ or "{}"),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
            if len(results) >= top_k:
                break

        return results

    def get_recent(self, limit: int = 10, source: str | None = None) -> list[dict]:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        q = db.query(AHMemory)
        if source:
            q = q.filter(AHMemory.source == source)
        rows = q.order_by(AHMemory.created_at.desc()).limit(limit).all()
        return [self._to_dict(r) for r in rows]

    def delete(self, memory_id: int) -> bool:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        m = db.query(AHMemory).filter_by(id=memory_id).first()
        if m:
            db.delete(m)
            db.commit()
            return True
        return False

    def _to_dict(self, r: Any) -> dict:
        return {
            "id": r.id,
            "content": r.content,
            "source": r.source,
            "tags": json.loads(r.tags or "[]"),
            "importance": r.importance,
            "metadata": json.loads(r.metadata_ or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }


memory_store = MemoryStore()
