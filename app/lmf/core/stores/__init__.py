"""
ArcHillx — LMF Store Accessors
==============================
Thin DB-backed stores for each LMF memory tier.
All stores are lazy-initialized singletons that write directly to the
SQLAlchemy models in app.db.schema.

Stores:
  EpisodicStore    → ah_lmf_episodic
  SemanticStore    → ah_lmf_semantic
  ProceduralStore  → ah_lmf_procedural
  WorkingStore     → ah_lmf_working

get_lmf_stats() returns row counts for all tiers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Episodic Store
# ══════════════════════════════════════════════════════════════════════════════

class _EpisodicStore:
    """DB-backed episodic memory store."""

    def add(
        self,
        *,
        event_type: str,
        content: str,
        source: str = "archillx",
        task_id: Optional[int] = None,
        session_id: Optional[int] = None,
        importance: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> int:
        from ...db.schema import SessionLocal, AHLMFEpisodic
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        db = SessionLocal()
        try:
            row = AHLMFEpisodic(
                event_type=event_type,
                content=content,
                content_hash=content_hash,
                source=source,
                task_id=task_id,
                session_id=session_id,
                importance=importance,
                tags=json.dumps(tags or []),
                metadata_=json.dumps(metadata or {}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    def search(
        self,
        *,
        q: str = "",
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHLMFEpisodic
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            query = db.query(AHLMFEpisodic).order_by(desc(AHLMFEpisodic.created_at))
            if event_type:
                query = query.filter(AHLMFEpisodic.event_type == event_type)
            if q:
                query = query.filter(AHLMFEpisodic.content.ilike(f"%{q}%"))
            rows = query.limit(limit).all()
            return [
                {
                    "id": r.id,
                    "event_type": r.event_type,
                    "content": r.content,
                    "content_hash": r.content_hash,
                    "source": r.source,
                    "task_id": r.task_id,
                    "session_id": r.session_id,
                    "importance": r.importance,
                    "tags": json.loads(r.tags or "[]"),
                    "metadata": json.loads(r.metadata_ or "{}"),
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Semantic Store
# ══════════════════════════════════════════════════════════════════════════════

class _SemanticStore:
    """DB-backed semantic memory store (concept/entity)."""

    def upsert(
        self,
        *,
        concept: str,
        content: str,
        source: str = "archillx",
        confidence: float = 1.0,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> int:
        from ...db.schema import SessionLocal, AHLMFSemantic
        db = SessionLocal()
        try:
            row = (
                db.query(AHLMFSemantic)
                .filter(AHLMFSemantic.concept == concept)
                .first()
            )
            if row:
                row.content = content
                row.source = source
                row.confidence = confidence
                row.tags = json.dumps(tags or [])
                row.metadata_ = json.dumps(metadata or {})
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
                return row.id
            row = AHLMFSemantic(
                concept=concept,
                content=content,
                source=source,
                confidence=confidence,
                tags=json.dumps(tags or []),
                metadata_=json.dumps(metadata or {}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    def search(self, *, q: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHLMFSemantic
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            query = db.query(AHLMFSemantic).order_by(desc(AHLMFSemantic.updated_at))
            if q:
                query = query.filter(
                    AHLMFSemantic.concept.ilike(f"%{q}%")
                    | AHLMFSemantic.content.ilike(f"%{q}%")
                )
            rows = query.limit(limit).all()
            return [
                {
                    "id": r.id,
                    "concept": r.concept,
                    "content": r.content,
                    "source": r.source,
                    "confidence": r.confidence,
                    "tags": json.loads(r.tags or "[]"),
                    "metadata": json.loads(r.metadata_ or "{}"),
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Procedural Store
# ══════════════════════════════════════════════════════════════════════════════

class _ProceduralStore:
    """DB-backed procedural (skill execution log) store."""

    def log(
        self,
        *,
        skill_name: str,
        invocation: Dict[str, Any],
        outcome: str,
        duration_ms: int = 0,
        output_hash: Optional[str] = None,
        error_msg: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> int:
        from ...db.schema import SessionLocal, AHLMFProcedural
        db = SessionLocal()
        try:
            row = AHLMFProcedural(
                skill_name=skill_name,
                invocation=json.dumps(invocation),
                outcome=outcome,
                duration_ms=duration_ms,
                output_hash=output_hash,
                error_msg=error_msg,
                metadata_=json.dumps(metadata or {}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()

    def search(
        self,
        *,
        skill_name: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHLMFProcedural
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            query = db.query(AHLMFProcedural).order_by(desc(AHLMFProcedural.created_at))
            if skill_name:
                query = query.filter(AHLMFProcedural.skill_name == skill_name)
            if outcome:
                query = query.filter(AHLMFProcedural.outcome == outcome)
            rows = query.limit(limit).all()
            return [
                {
                    "id": r.id,
                    "skill_name": r.skill_name,
                    "invocation": json.loads(r.invocation or "{}"),
                    "outcome": r.outcome,
                    "duration_ms": r.duration_ms,
                    "output_hash": r.output_hash,
                    "error_msg": r.error_msg,
                    "metadata": json.loads(r.metadata_ or "{}"),
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Working Memory Store
# ══════════════════════════════════════════════════════════════════════════════

class _WorkingStore:
    """DB-backed transient working memory (task-scoped, auto-expires)."""

    def set(
        self,
        *,
        task_id: int,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        from ...db.schema import SessionLocal, AHLMFWorking
        import datetime as dt
        db = SessionLocal()
        try:
            row = (
                db.query(AHLMFWorking)
                .filter(AHLMFWorking.task_id == task_id, AHLMFWorking.key == key)
                .first()
            )
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + dt.timedelta(seconds=ttl_seconds)
            if row:
                row.value = json.dumps(value)
                row.expires_at = expires_at
            else:
                row = AHLMFWorking(
                    task_id=task_id,
                    key=key,
                    value=json.dumps(value),
                    expires_at=expires_at,
                )
                db.add(row)
            db.commit()
        finally:
            db.close()

    def get(self, task_id: int, key: str) -> Optional[Any]:
        from ...db.schema import SessionLocal, AHLMFWorking
        db = SessionLocal()
        try:
            row = (
                db.query(AHLMFWorking)
                .filter(AHLMFWorking.task_id == task_id, AHLMFWorking.key == key)
                .first()
            )
            if not row:
                return None
            if row.expires_at and row.expires_at < datetime.utcnow():
                db.delete(row)
                db.commit()
                return None
            return json.loads(row.value)
        finally:
            db.close()

    def get_all(self, task_id: int) -> List[Dict[str, Any]]:
        from ...db.schema import SessionLocal, AHLMFWorking
        db = SessionLocal()
        try:
            rows = db.query(AHLMFWorking).filter(AHLMFWorking.task_id == task_id).all()
            now = datetime.utcnow()
            result = []
            for r in rows:
                if r.expires_at and r.expires_at < now:
                    continue
                result.append({
                    "key": r.key,
                    "value": json.loads(r.value),
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "created_at": r.created_at.isoformat(),
                })
            return result
        finally:
            db.close()

    def clear(self, task_id: int) -> None:
        from ...db.schema import SessionLocal, AHLMFWorking
        db = SessionLocal()
        try:
            db.query(AHLMFWorking).filter(AHLMFWorking.task_id == task_id).delete()
            db.commit()
        finally:
            db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Aggregated stats
# ══════════════════════════════════════════════════════════════════════════════

def get_lmf_stats() -> Dict[str, int]:
    """Return row counts across all LMF tiers."""
    from ...db.schema import (
        SessionLocal, AHLMFEpisodic, AHLMFSemantic,
        AHLMFProcedural, AHLMFWorking, AHLMFCausal, AHLMFWal,
    )
    db = SessionLocal()
    try:
        return {
            "episodic":   db.query(AHLMFEpisodic).count(),
            "semantic":   db.query(AHLMFSemantic).count(),
            "procedural": db.query(AHLMFProcedural).count(),
            "working":    db.query(AHLMFWorking).count(),
            "causal":     db.query(AHLMFCausal).count(),
            "wal":        db.query(AHLMFWal).count(),
        }
    finally:
        db.close()


# ── Singletons ────────────────────────────────────────────────────────────────

_episodic_store:   Optional[_EpisodicStore]   = None
_semantic_store:   Optional[_SemanticStore]   = None
_procedural_store: Optional[_ProceduralStore] = None
_working_store:    Optional[_WorkingStore]    = None


def get_episodic_store() -> _EpisodicStore:
    global _episodic_store
    if _episodic_store is None:
        _episodic_store = _EpisodicStore()
    return _episodic_store


def get_semantic_store() -> _SemanticStore:
    global _semantic_store
    if _semantic_store is None:
        _semantic_store = _SemanticStore()
    return _semantic_store


def get_procedural_store() -> _ProceduralStore:
    global _procedural_store
    if _procedural_store is None:
        _procedural_store = _ProceduralStore()
    return _procedural_store


def get_working_store() -> _WorkingStore:
    global _working_store
    if _working_store is None:
        _working_store = _WorkingStore()
    return _working_store
