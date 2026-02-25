"""
ArcHeli v1.0.0 — Configuration
Standalone autonomous AI system.
Inherits multi-database pattern from MGIS (SQLite / MySQL / MSSQL).
"""
from __future__ import annotations

import os
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "ArcHeli"
    app_version: str = "1.0.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    # db_type controls which engine is used.
    # Note: SQLite is for development only. Production should use mysql/mssql.
    db_type: Literal["sqlite", "sqlite_memory", "mysql", "mssql"] = "sqlite"
    db_name: str = "archeli"          # SQLite: file name (archeli.db); MySQL/MSSQL: schema/db name
    db_host: str = "localhost"
    db_port: int = 3306               # MySQL default; MSSQL use 1433
    db_user: str = "root"
    db_password: str = ""

    # MySQL / MSSQL connection pool (ignored for SQLite)
    db_pool_size: int = 5             # Core persistent connections
    db_max_overflow: int = 10         # Burst connections above pool_size
    db_pool_timeout: int = 30         # Seconds to wait for a free connection
    db_pool_recycle: int = 3600       # Recycle connections to prevent stale state

    # ── AI Providers ─────────────────────────────────────────────────────────
    # Set any key to enable that provider automatically.

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # OpenAI-compatible
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Google Gemini
    google_api_key: str = ""

    # Groq (ultra-fast inference)
    groq_api_key: str = ""

    # Mistral
    mistral_api_key: str = ""

    # OLLAMA local model  (OLLAMA_ENABLED=true to activate)
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_default_model: str = "llama3.2"

    # Custom OpenAI-compatible endpoint (LM Studio / DeepSeek / Together / etc.)
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
    api_key: str = ""          # Required for /v1/* endpoints (empty = no auth)
    admin_token: str = ""

    # ── Constructed Database URL ──────────────────────────────────────────────
    @property
    def database_url(self) -> str:
        # Allow full override via DATABASE_URL env var (12-factor style)
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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
