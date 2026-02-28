"""
ArcHillx v1.0.0 — Lightweight Memory Store
Keyword + importance 搜尋，不需要 vector DB 或外部依賴。
若 OLLAMA 可用則自動升級為向量搜尋（未來擴充點）。
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("archillx.memory")


class MemoryStore:
    """
    輕量記憶儲存：
    - 寫入 ah_memory 表
    - 以關鍵字召回 + 重要度/新鮮度重排序
    - 支援 tag / source / min_importance 過濾
    """

    def add(self, content: str, source: str = "archillx",
            tags: list[str] | None = None,
            importance: float = 0.5,
            metadata: dict | None = None) -> int:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        try:
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
        finally:
            db.close()

    def query(self, query: str, top_k: int = 5,
              tags: list[str] | None = None,
              min_importance: float = 0.0,
              source: str | None = None) -> list[dict]:
        """
        關鍵字搜尋記憶。
        舊版為 token AND + LIKE，容易越搜越窄。
        新版改為：
        1. token OR 召回候選
        2. phrase / token-hit / importance / recency 綜合打分
        3. tag / source 後過濾
        """
        from sqlalchemy import or_
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        try:
            q = db.query(AHMemory)
            if source:
                q = q.filter(AHMemory.source == source)
            if min_importance > 0:
                q = q.filter(AHMemory.importance >= min_importance)

            norm_query = self._normalize_text(query)
            tokens = self._tokenize(norm_query)

            if norm_query:
                if tokens:
                    clauses = [AHMemory.content.ilike(f"%{tok}%") for tok in tokens[:8]]
                    q = q.filter(or_(*clauses))
                else:
                    q = q.filter(AHMemory.content.ilike(f"%{norm_query}%"))

            candidate_limit = max(top_k * 8, 20)
            rows = q.order_by(AHMemory.importance.desc(), AHMemory.created_at.desc()).limit(candidate_limit).all()

            wanted_tags = set(tags or [])
            scored: list[tuple[float, Any]] = []
            for r in rows:
                row_tags = set(json.loads(r.tags or "[]"))
                if wanted_tags and not (wanted_tags & row_tags):
                    continue
                score = self._score_row(r, norm_query, tokens, wanted_tags)
                if score <= 0 and norm_query:
                    continue
                scored.append((score, r))

            scored.sort(key=lambda item: item[0], reverse=True)
            return [self._to_dict(r, score=round(score, 4)) for score, r in scored[:top_k]]
        finally:
            db.close()

    def get_recent(self, limit: int = 10, source: str | None = None) -> list[dict]:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        try:
            q = db.query(AHMemory)
            if source:
                q = q.filter(AHMemory.source == source)
            rows = q.order_by(AHMemory.created_at.desc()).limit(limit).all()
            return [self._to_dict(r) for r in rows]
        finally:
            db.close()

    def delete(self, memory_id: int) -> bool:
        from ..db.schema import AHMemory, get_db
        db = next(get_db())
        try:
            m = db.query(AHMemory).filter_by(id=memory_id).first()
            if m:
                db.delete(m)
                db.commit()
                return True
            return False
        finally:
            db.close()

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        if " " in text:
            return [t for t in text.split() if len(t) > 1][:8]
        chunks = re.findall(r"[一-鿿]{2,4}|[a-z0-9_\-]{2,}", text.lower())
        if chunks:
            return chunks[:8]
        return [text] if len(text) > 1 else []

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def _score_row(self, row: Any, norm_query: str, tokens: list[str], wanted_tags: set[str]) -> float:
        content = self._normalize_text(row.content or "")
        if not norm_query:
            return float(row.importance or 0)

        score = 0.0
        if norm_query and norm_query in content:
            score += 4.0

        hit_counts = Counter(tok for tok in tokens if tok in content)
        score += sum(1.2 for _ in hit_counts)
        score += sum(min(content.count(tok), 3) * 0.2 for tok in hit_counts)

        if wanted_tags:
            row_tags = set(json.loads(row.tags or "[]"))
            overlap = len(wanted_tags & row_tags)
            score += overlap * 0.6

        importance = max(0.0, min(1.0, float(row.importance or 0.0)))
        score += importance * 2.0

        created_at = row.created_at
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = max((datetime.now(timezone.utc) - created_at).total_seconds() / 3600.0, 0.0)
            if age_hours <= 24:
                score += 0.6
            elif age_hours <= 24 * 7:
                score += 0.3

        return score

    def _to_dict(self, r: Any, score: float | None = None) -> dict:
        data = {
            "id": r.id,
            "content": r.content,
            "source": r.source,
            "tags": json.loads(r.tags or "[]"),
            "importance": r.importance,
            "metadata": json.loads(r.metadata_ or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        if score is not None:
            data["score"] = score
        return data


memory_store = MemoryStore()
