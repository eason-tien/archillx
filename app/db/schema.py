"""
ArcHeli v1.0.0 — Database Schema
Supports SQLite (dev) / MySQL (production) / MSSQL (enterprise).
Engine factory mirrors the MGIS multi-DB pattern.
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from typing import Generator

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    create_engine, event, text
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool


# ── Engine factory ────────────────────────────────────────────────────────────

@lru_cache()
def _make_engine():
    """
    Create the SQLAlchemy engine based on DB_TYPE in settings.
    Cached so the same engine is reused across the process lifetime.
    """
    from ..config import settings

    db_url = settings.database_url
    db_type = settings.db_type

    if db_type == "mysql":
        # Production: QueuePool with health-check pre-ping
        return create_engine(
            db_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            future=True,
        )

    if db_type == "mssql":
        # Enterprise: basic engine (MSSQL driver handles pooling)
        return create_engine(db_url, future=True)

    if db_type == "sqlite_memory":
        # In-memory SQLite for testing — StaticPool keeps single connection alive
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )

    # Default: SQLite file — NullPool avoids threading issues
    return create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        future=True,
    )


engine = _make_engine()


# ── SQLite-only PRAGMA setup ──────────────────────────────────────────────────

@event.listens_for(engine, "connect")
def _configure_connection(conn, _record):
    """Apply SQLite PRAGMAs; silently skip for MySQL / MSSQL."""
    from ..config import settings
    if settings.db_type in ("sqlite", "sqlite_memory"):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")


# ── Session factory ───────────────────────────────────────────────────────────

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ── ORM Models ────────────────────────────────────────────────────────────────

class AHSession(Base):
    __tablename__ = "ah_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(128), nullable=False)
    status     = Column(String(32), default="active")         # active|closed
    context    = Column(Text, default="{}")                   # JSON
    goal_ids   = Column(Text, default="[]")                   # JSON list of int
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_sessions_status", "status"),
        Index("ix_ah_sessions_created_at", "created_at"),
    )


class AHTask(Base):
    __tablename__ = "ah_tasks"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, nullable=True, index=True)
    title        = Column(String(256), nullable=False)
    skill_name   = Column(String(128), nullable=True)
    task_type    = Column(String(64), default="general")
    status       = Column(String(32), default="created")
    # created | assigned | executing | verifying | closed | failed
    input_data   = Column(Text, default="{}")                 # JSON
    output_data  = Column(Text, default="{}")                 # JSON
    governor_ok  = Column(Boolean, default=False)
    model_used   = Column(String(64), nullable=True)
    tokens_used  = Column(Integer, default=0)
    error_msg    = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at    = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_ah_tasks_status", "status"),
        Index("ix_ah_tasks_skill_name", "skill_name"),
        Index("ix_ah_tasks_task_type", "task_type"),
        Index("ix_ah_tasks_created_at", "created_at"),
    )


class AHAgent(Base):
    __tablename__ = "ah_agents"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    session_id    = Column(Integer, nullable=True, index=True)
    agent_type    = Column(String(64), default="general")
    status        = Column(String(32), default="idle")        # idle|running|terminated
    current_task  = Column(Integer, nullable=True)
    metadata_     = Column(Text, default="{}")                # JSON
    created_at    = Column(DateTime, default=datetime.utcnow)
    terminated_at = Column(DateTime, nullable=True)


class AHGoal(Base):
    __tablename__ = "ah_goals"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(256), nullable=False)
    description = Column(Text, default="")
    status      = Column(String(32), default="active")
    # active | paused | completed | abandoned
    progress    = Column(Float, default=0.0)                  # 0.0–1.0
    priority    = Column(Integer, default=5)                  # 1 (low) – 10 (high)
    context     = Column(Text, default="{}")                  # JSON
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_goals_status", "status"),
        Index("ix_ah_goals_priority", "priority"),
    )


class AHSkill(Base):
    __tablename__ = "ah_skills"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(128), unique=True, nullable=False)
    version      = Column(String(32), default="1.0")
    description  = Column(Text, default="")
    manifest     = Column(Text, default="{}")                 # JSON (full manifest)
    source       = Column(String(32), default="local")        # local | remote
    enabled      = Column(Boolean, default=True)
    invoke_count = Column(Integer, default=0)
    error_count  = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AHCronJob(Base):
    __tablename__ = "ah_cron_jobs"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    name              = Column(String(128), unique=True, nullable=False)
    cron_expr         = Column(String(64), nullable=True)     # "0 9 * * *"
    interval_s        = Column(Integer, nullable=True)        # seconds; mutually exclusive with cron_expr
    skill_name        = Column(String(128), nullable=False)
    input_data        = Column(Text, default="{}")            # JSON passed to skill
    enabled           = Column(Boolean, default=True)
    governor_required = Column(Boolean, default=True)
    last_run          = Column(DateTime, nullable=True)
    next_run          = Column(DateTime, nullable=True)
    run_count         = Column(Integer, default=0)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AHBrowserSession(Base):
    __tablename__ = "ah_browser_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    task_id    = Column(Integer, nullable=True, index=True)
    url        = Column(Text, nullable=True)
    status     = Column(String(32), default="active")         # active|closed|error
    actions    = Column(Text, default="[]")                   # JSON list of action dicts
    screenshot = Column(Text, nullable=True)                  # base64 PNG
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at  = Column(DateTime, nullable=True)


class AHMemory(Base):
    """Lightweight semantic memory — keyword-searchable, no vector DB required."""
    __tablename__ = "ah_memory"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    content    = Column(Text, nullable=False)
    source     = Column(String(64), default="archeli")
    tags       = Column(Text, default="[]")                   # JSON list of strings
    importance = Column(Float, default=0.5)                   # 0.0–1.0
    metadata_  = Column(Text, default="{}")                   # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_memory_source", "source"),
        Index("ix_ah_memory_importance", "importance"),
        Index("ix_ah_memory_created_at", "created_at"),
    )


class AHAuditLog(Base):
    __tablename__ = "ah_audit_log"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    action     = Column(String(256), nullable=False)
    decision   = Column(String(16), nullable=False)           # APPROVED|BLOCKED|WARNED
    risk_score = Column(Integer, default=0)
    reason     = Column(Text, nullable=True)
    context    = Column(Text, default="{}")                   # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_audit_log_decision", "decision"),
        Index("ix_ah_audit_log_created_at", "created_at"),
    )


# ── DB lifecycle ──────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables (idempotent — skips existing tables)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session and close on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
