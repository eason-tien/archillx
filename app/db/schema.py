"""
ArcHillx v1.0.0 — Database Schema
Supports SQLite (dev) / MySQL (production) / MSSQL (enterprise).
Engine factory mirrors the MGIS multi-DB pattern.

Tables:
  Core:   ah_sessions, ah_tasks, ah_agents, ah_goals, ah_skills,
          ah_cron_jobs, ah_browser_sessions, ah_memory, ah_audit_log
  LMF:    ah_lmf_episodic, ah_lmf_semantic, ah_lmf_procedural,
          ah_lmf_working, ah_lmf_causal, ah_lmf_wal,
          ah_lmf_risk_profiles, ah_lmf_risk_profile_history,
          ah_lmf_v6_feedback_signatures
  Planner: ah_planner_taskgraphs, ah_planner_resources
  Rollout: ah_rollout_metrics, ah_rollout_policy
  Proactive: ah_projects, ah_drivers, ah_sprint_plans
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from typing import Generator

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, LargeBinary,
    String, Text, create_engine, event
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
    source     = Column(String(64), default="archillx")
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


# ══════════════════════════════════════════════════════════════════════════════
#  LMF Tables — Language Memory Framework (five tiers)
#  Activated when ENABLE_LMF=true in .env
# ══════════════════════════════════════════════════════════════════════════════

class AHLMFEpisodic(Base):
    """Episodic memory: timestamped events with evidence hashes."""
    __tablename__ = "ah_lmf_episodic"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    event_type   = Column(String(64), nullable=False)          # TASK_COMPLETE|SKILL_INVOKE|etc.
    content      = Column(Text, nullable=False)                # Human-readable description
    content_hash = Column(String(64), nullable=True)           # SHA-256 of content
    source       = Column(String(64), default="archillx")
    task_id      = Column(Integer, nullable=True, index=True)
    session_id   = Column(Integer, nullable=True, index=True)
    importance   = Column(Float, default=0.5)
    tags         = Column(Text, default="[]")                  # JSON list
    metadata_    = Column(Text, default="{}")                  # JSON
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_episodic_event_type", "event_type"),
        Index("ix_ah_lmf_episodic_created_at", "created_at"),
    )


class AHLMFSemantic(Base):
    """Semantic memory: concepts, entities, facts with optional vector hint."""
    __tablename__ = "ah_lmf_semantic"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    concept      = Column(String(256), nullable=False)         # Entity / concept label
    content      = Column(Text, nullable=False)                # Detailed description
    source       = Column(String(64), default="archillx")
    confidence   = Column(Float, default=1.0)                  # 0.0–1.0
    tags         = Column(Text, default="[]")                  # JSON
    embedding_hint = Column(Text, nullable=True)               # JSON float list (optional)
    metadata_    = Column(Text, default="{}")                  # JSON
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_semantic_concept", "concept"),
        Index("ix_ah_lmf_semantic_source", "source"),
    )


class AHLMFProcedural(Base):
    """Procedural memory: skill execution logs and learned patterns."""
    __tablename__ = "ah_lmf_procedural"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    skill_name   = Column(String(128), nullable=False, index=True)
    invocation   = Column(Text, nullable=False)                # JSON of input_data
    outcome      = Column(String(16), nullable=False)          # success|failure
    duration_ms  = Column(Integer, default=0)
    output_hash  = Column(String(64), nullable=True)
    error_msg    = Column(Text, nullable=True)
    metadata_    = Column(Text, default="{}")                  # JSON
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_procedural_outcome", "outcome"),
        Index("ix_ah_lmf_procedural_created_at", "created_at"),
    )


class AHLMFWorking(Base):
    """Working memory: transient task-scoped state (auto-expires)."""
    __tablename__ = "ah_lmf_working"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    task_id    = Column(Integer, nullable=False, index=True)
    key        = Column(String(128), nullable=False)
    value      = Column(Text, nullable=False)                  # JSON value
    expires_at = Column(DateTime, nullable=True)               # None = session-scoped
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_working_task_key", "task_id", "key"),
    )


class AHLMFCausal(Base):
    """Causal graph nodes: root-cause and effect relationships."""
    __tablename__ = "ah_lmf_causal"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    node_type    = Column(String(32), nullable=False)          # CAUSE|EFFECT|PATTERN
    description  = Column(Text, nullable=False)
    parent_id    = Column(Integer, nullable=True, index=True)  # FK to self (causal chain)
    confidence   = Column(Float, default=1.0)
    evidence     = Column(Text, default="[]")                  # JSON list of evidence refs
    task_id      = Column(Integer, nullable=True, index=True)
    metadata_    = Column(Text, default="{}")
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_causal_node_type", "node_type"),
    )


class AHLMFWal(Base):
    """Write-Ahead Log: pre-committed memory writes for crash recovery."""
    __tablename__ = "ah_lmf_wal"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    store_tier   = Column(String(32), nullable=False)          # episodic|semantic|procedural|etc.
    operation    = Column(String(16), nullable=False)          # INSERT|UPDATE|DELETE
    payload      = Column(Text, nullable=False)                # JSON
    committed    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_lmf_wal_committed", "committed"),
    )


class AHLMFRiskProfile(Base):
    """Risk profiles for adaptive governor (EvolutionLoop)."""
    __tablename__ = "ah_lmf_risk_profiles"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    action_key   = Column(String(128), unique=True, nullable=False)
    base_risk    = Column(Integer, default=50)                 # 0–100
    metadata_    = Column(Text, default="{}")
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AHLMFRiskProfileHistory(Base):
    """History of risk profile adjustments."""
    __tablename__ = "ah_lmf_risk_profile_history"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    action_key    = Column(String(128), nullable=False, index=True)
    old_base_risk = Column(Integer, nullable=False)
    new_base_risk = Column(Integer, nullable=False)
    reason        = Column(String(256), nullable=True)
    metrics_json  = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


class AHLMFV6FeedbackSignature(Base):
    """Multi-agent feedback deduplication signatures."""
    __tablename__ = "ah_lmf_v6_feedback_signatures"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    executor_id    = Column(String(128), nullable=False, index=True)
    error_signature = Column(String(64), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
#  Planner Tables
# ══════════════════════════════════════════════════════════════════════════════

class AHPlannerTaskGraph(Base):
    """Serialised TaskGraph snapshots for the planning system."""
    __tablename__ = "ah_planner_taskgraphs"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    goal_id      = Column(Integer, nullable=True, index=True)
    session_id   = Column(Integer, nullable=True, index=True)
    title        = Column(String(256), nullable=False)
    status       = Column(String(32), default="pending")       # pending|running|done|failed
    graph_json   = Column(Text, nullable=False)                # Serialised TaskGraph
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
#  Rollout Tables (Canary)
# ══════════════════════════════════════════════════════════════════════════════

class AHRolloutMetric(Base):
    """Per-plan-signature canary / control metrics."""
    __tablename__ = "ah_rollout_metrics"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    plan_signature = Column(String(64), nullable=False, index=True)
    bucket         = Column(String(16), nullable=False)        # canary|control
    success        = Column(Boolean, nullable=False)
    latency_ms     = Column(Integer, default=0)
    cost           = Column(Float, default=0.0)
    created_at     = Column(DateTime, default=datetime.utcnow)


class AHRolloutPolicy(Base):
    """Active rollout policy per plan signature."""
    __tablename__ = "ah_rollout_policy"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    plan_signature = Column(String(64), unique=True, nullable=False)
    stage          = Column(String(32), default="CONTROL")     # CONTROL|CANARY_5|CANARY_20|FULL_100
    promoted_at    = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    metadata_      = Column(Text, default="{}")
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
#  Proactive Intelligence Tables
# ══════════════════════════════════════════════════════════════════════════════

class AHProject(Base):
    """Proactive intelligence: active projects / workstreams."""
    __tablename__ = "ah_projects"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(128), unique=True, nullable=False)
    goal_statement  = Column(Text, default="")
    status          = Column(String(32), default="ACTIVE")     # ACTIVE|LIMITED|DISABLED|FROZEN
    reject_streak   = Column(Integer, default=0)
    metadata_       = Column(Text, default="{}")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AHDriver(Base):
    """Daily drivers: BLOCKER, RISK, DEPENDENCY, OPPORTUNITY, DEBT items."""
    __tablename__ = "ah_drivers"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    project_id  = Column(Integer, nullable=True, index=True)
    driver_type = Column(String(32), nullable=False)           # BLOCKER|RISK|DEPENDENCY|OPPORTUNITY|DEBT
    content     = Column(Text, nullable=False)
    priority    = Column(Integer, default=5)
    resolved    = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ah_drivers_driver_type", "driver_type"),
        Index("ix_ah_drivers_resolved", "resolved"),
    )


class AHSprintPlan(Base):
    """Weekly sprint plans generated by SprintPlanner."""
    __tablename__ = "ah_sprint_plans"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    project_id  = Column(Integer, nullable=True, index=True)
    week_start  = Column(DateTime, nullable=False)
    goals_json  = Column(Text, default="[]")                   # JSON list of sprint goals
    backlog_json = Column(Text, default="[]")                  # JSON list of backlog items
    status      = Column(String(32), default="draft")          # draft|active|completed
    created_at  = Column(DateTime, default=datetime.utcnow)


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
