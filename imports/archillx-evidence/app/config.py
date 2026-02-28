"""
ArcHillx v1.0.0 — Configuration
Standalone autonomous AI system.
Full feature parity with MGIS: multi-database, feature flags, provider routing.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_app_version() -> str:
    env_version = os.getenv("APP_VERSION", "").strip()
    if env_version:
        return env_version
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        value = version_file.read_text(encoding="utf-8").strip()
        return value or "1.0.0"
    except OSError:
        return "1.0.0"


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "ArcHillx"
    app_version: str = _read_app_version()
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    # Note: SQLite is for development only. Production must use mysql/mssql.
    db_type: Literal["sqlite", "sqlite_memory", "mysql", "mssql"] = "sqlite"
    db_name: str = "archillx"
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""

    # Connection pool (MySQL / MSSQL only)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600

    # ── AI Providers ─────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    google_api_key: str = ""
    groq_api_key: str = ""
    mistral_api_key: str = ""
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_default_model: str = "llama3.2"
    custom_model_base_url: str = ""
    custom_model_api_key: str = ""
    custom_model_name: str = "custom"

    # ── Routing ───────────────────────────────────────────────────────────────
    routing_rules_path: str = "./configs/routing_rules.yaml"

    # ── Governor ──────────────────────────────────────────────────────────────
    governor_mode: str = "soft_block"   # soft_block | hard_block | audit_only | off
    risk_block_threshold: int = 90
    risk_warn_threshold: int = 70

    # ── Paths ─────────────────────────────────────────────────────────────────
    skills_dir: str = "./app/skills"
    evidence_dir: str = "./evidence"
    cron_timezone: str = "Asia/Taipei"

    # ── Security ──────────────────────────────────────────────────────────────
    api_key: str = ""
    admin_token: str = ""
    enable_rate_limit: bool = False
    rate_limit_per_min: int = 120
    high_risk_rate_limit_per_min: int = 15
    audit_file_max_bytes: int = 5 * 1024 * 1024
    enable_metrics: bool = True
    enable_migration_check: bool = True
    require_migration_head: bool = True

    # ── Evolution / Self-Improvement ─────────────────────────────────────────

    enable_evolution: bool = True
    enable_evolution_auto: bool = False
    evolution_auto_cycle_cron: str = "15 */6 * * *"
    evolution_auto_generate_limit: int = 3
    evolution_auto_guard_low_risk: bool = True
    evolution_auto_guard_mode: str = "quick"
    evolution_auto_approve_low_risk: bool = False
    evolution_auto_approve_requires_guard_pass: bool = True
    evolution_auto_approve_actor: str = "evolution-auto"
    evolution_auto_apply_low_risk: bool = False
    evolution_auto_apply_requires_guard_pass: bool = True
    evolution_auto_apply_requires_baseline_clear: bool = True
    evolution_auto_apply_actor: str = "evolution-auto"


    # ═══════════════════════════════════════════════════════════════════════
    #  Feature Flags — inherited from MGIS graduated rollout model
    #  All default to False for safe gradual activation.
    # ═══════════════════════════════════════════════════════════════════════

    # ── Memory / LMF ─────────────────────────────────────────────────────────
    # Five-tier Language Memory Framework (Episodic/Semantic/Procedural/Causal/Working)
    enable_lmf: bool = False
    enable_lmf_episodic: bool = False       # Event-based memory with evidence hashes
    enable_lmf_semantic: bool = False       # Concept/entity semantic memory
    enable_lmf_procedural: bool = False     # Skill execution history & patterns
    enable_lmf_causal: bool = False         # Causal graph: nodes, edges, patterns
    enable_lmf_working: bool = False        # Transient task-scoped working memory
    enable_lmf_wal: bool = False            # Write-Ahead Log for crash recovery
    enable_lmf_consolidator: bool = False   # Periodic memory consolidation
    enable_lmf_blob: bool = False           # Large artifact / blob storage

    # ── Causal Analysis ───────────────────────────────────────────────────────
    enable_causal_abstraction: bool = False  # Causal node/link abstraction layer
    enable_causal_drift: bool = False        # Distribution drift detection
    enable_causal_compression: bool = False  # Causal graph compression

    # ── Governor Advanced ─────────────────────────────────────────────────────
    enable_adaptive_governor: bool = False   # RL-based online policy adaptation
    enable_consensus_governor: bool = False  # Bayesian weighted multi-evaluator
    enable_multi_agent_governor: bool = False  # Master governor + circuit breaker

    # ── Autonomy & Remediation ────────────────────────────────────────────────
    enable_autonomous_remediation: bool = False  # Auto root-cause + fix planning
    enable_plan_search: bool = False             # Beam search over remedy space
    enable_ranked_shadow: bool = False           # Thompson sampling shadow exec
    enable_shadow_reliability: bool = False      # Shadow plan reliability metrics
    enable_weight_tuning: bool = False           # Online weight adaptation
    enable_counterfactual_learning: bool = False # Counterfactual trajectory analysis
    enable_canary_rollout: bool = False          # Staged rollout with metric guard
    enable_rollout_stats_guard: bool = False     # Stats-based rollout promotion

    # ── Planning ──────────────────────────────────────────────────────────────
    enable_planner: bool = False            # Hierarchical task graph planning
    enable_goal_inference: bool = False     # Multi-hypothesis goal tracking
    enable_resource_registry: bool = False  # Tool/capability inventory

    # ── Proactive Intelligence ────────────────────────────────────────────────
    enable_proactive: bool = False          # Master proactive intelligence switch
    enable_daily_driver: bool = False       # Daily autonomous task generation
    enable_sprint_planner: bool = False     # Weekly sprint planning
    enable_message_classifier: bool = False # Incoming message classification

    # ── Notifications ─────────────────────────────────────────────────────────
    enable_notifications: bool = False
    enable_slack_notifications: bool = False
    enable_telegram_notifications: bool = False
    enable_webhook_notifications: bool = False
    enable_websocket_notifications: bool = False

    # Notification channels config
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    notification_webhook_url: str = ""

    # ── Skill Advanced ────────────────────────────────────────────────────────
    enable_skill_acl: bool = False          # Skill access control lists
    enable_skill_rollback: bool = False     # Transaction-like skill rollback
    enable_skill_validation: bool = False   # Pre-execution skill validation

    # ── Integrations ──────────────────────────────────────────────────────────
    enable_openclaw_integration: bool = False
    enable_trae_solo_integration: bool = False
    openclaw_base_url: str = "http://localhost:9000"
    openclaw_api_key: str = ""
    trae_solo_base_url: str = "http://localhost:9100"
    trae_solo_api_key: str = ""

    # ── Resource Guard ────────────────────────────────────────────────────────
    enable_resource_guard: bool = False
    resource_max_memory_mb: int = 512
    resource_max_cpu_percent: float = 80.0
    resource_max_skill_calls_per_min: int = 60

    # ── Telemetry ─────────────────────────────────────────────────────────────
    enable_telemetry: bool = False
    telemetry_endpoint: str = ""           # Prometheus push gateway or OTLP endpoint
    telemetry_service_name: str = "archillx"

    # ── Proactive schedule (when enable_proactive=True) ───────────────────────
    daily_driver_cron: str = "30 21 * * *"    # Default 21:30 daily
    sprint_planner_cron: str = "0 18 * * 0"   # Default Sunday 18:00

    # ── Constructed Database URL ──────────────────────────────────────────────
    @property
    def database_url(self) -> str:
        override = os.getenv("DATABASE_URL")
        if override:
            return override
        if self.db_type == "sqlite":
            return f"sqlite:///./{self.db_name}.db"
        if self.db_type == "sqlite_memory":
            return "sqlite:///:memory:"
        if self.db_type == "mysql":
            return (
                f"mysql+pymysql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        if self.db_type == "mssql":
            return (
                f"mssql+pyodbc://{self.db_user}:{self.db_password}"
                f"@{self.db_host}/{self.db_name}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )
        return f"sqlite:///./{self.db_name}.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
