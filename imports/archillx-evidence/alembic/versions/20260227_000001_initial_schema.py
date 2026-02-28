"""initial schema

Revision ID: 20260227_000001
Revises:
Create Date: 2026-02-27 10:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260227_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ah_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("goal_ids", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_sessions_status", "ah_sessions", ["status"], unique=False)
    op.create_index("ix_ah_sessions_created_at", "ah_sessions", ["created_at"], unique=False)

    op.create_table(
        "ah_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("skill_name", sa.String(length=128), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("output_data", sa.Text(), nullable=True),
        sa.Column("governor_ok", sa.Boolean(), nullable=True),
        sa.Column("model_used", sa.String(length=64), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_tasks_session_id", "ah_tasks", ["session_id"], unique=False)
    op.create_index("ix_ah_tasks_status", "ah_tasks", ["status"], unique=False)
    op.create_index("ix_ah_tasks_skill_name", "ah_tasks", ["skill_name"], unique=False)
    op.create_index("ix_ah_tasks_task_type", "ah_tasks", ["task_type"], unique=False)
    op.create_index("ix_ah_tasks_created_at", "ah_tasks", ["created_at"], unique=False)

    op.create_table(
        "ah_agents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("agent_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("current_task", sa.Integer(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("terminated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_agents_session_id", "ah_agents", ["session_id"], unique=False)

    op.create_table(
        "ah_goals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_goals_status", "ah_goals", ["status"], unique=False)
    op.create_index("ix_ah_goals_priority", "ah_goals", ["priority"], unique=False)

    op.create_table(
        "ah_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manifest", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("invoke_count", sa.Integer(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name", name="uq_ah_skills_name"),
    )

    op.create_table(
        "ah_cron_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("cron_expr", sa.String(length=64), nullable=True),
        sa.Column("interval_s", sa.Integer(), nullable=True),
        sa.Column("skill_name", sa.String(length=128), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("governor_required", sa.Boolean(), nullable=True),
        sa.Column("last_run", sa.DateTime(), nullable=True),
        sa.Column("next_run", sa.DateTime(), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name", name="uq_ah_cron_jobs_name"),
    )

    op.create_table(
        "ah_browser_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("actions", sa.Text(), nullable=True),
        sa.Column("screenshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_browser_sessions_task_id", "ah_browser_sessions", ["task_id"], unique=False)

    op.create_table(
        "ah_memory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_memory_source", "ah_memory", ["source"], unique=False)
    op.create_index("ix_ah_memory_importance", "ah_memory", ["importance"], unique=False)
    op.create_index("ix_ah_memory_created_at", "ah_memory", ["created_at"], unique=False)

    op.create_table(
        "ah_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=256), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_audit_log_decision", "ah_audit_log", ["decision"], unique=False)
    op.create_index("ix_ah_audit_log_created_at", "ah_audit_log", ["created_at"], unique=False)

    op.create_table(
        "ah_lmf_episodic",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_episodic_task_id", "ah_lmf_episodic", ["task_id"], unique=False)
    op.create_index("ix_ah_lmf_episodic_session_id", "ah_lmf_episodic", ["session_id"], unique=False)
    op.create_index("ix_ah_lmf_episodic_event_type", "ah_lmf_episodic", ["event_type"], unique=False)
    op.create_index("ix_ah_lmf_episodic_created_at", "ah_lmf_episodic", ["created_at"], unique=False)

    op.create_table(
        "ah_lmf_semantic",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("concept", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("embedding_hint", sa.Text(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_semantic_concept", "ah_lmf_semantic", ["concept"], unique=False)
    op.create_index("ix_ah_lmf_semantic_source", "ah_lmf_semantic", ["source"], unique=False)

    op.create_table(
        "ah_lmf_procedural",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("skill_name", sa.String(length=128), nullable=False),
        sa.Column("invocation", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_procedural_skill_name", "ah_lmf_procedural", ["skill_name"], unique=False)
    op.create_index("ix_ah_lmf_procedural_outcome", "ah_lmf_procedural", ["outcome"], unique=False)
    op.create_index("ix_ah_lmf_procedural_created_at", "ah_lmf_procedural", ["created_at"], unique=False)

    op.create_table(
        "ah_lmf_working",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_working_task_id", "ah_lmf_working", ["task_id"], unique=False)
    op.create_index("ix_ah_lmf_working_task_key", "ah_lmf_working", ["task_id", "key"], unique=False)

    op.create_table(
        "ah_lmf_causal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_causal_parent_id", "ah_lmf_causal", ["parent_id"], unique=False)
    op.create_index("ix_ah_lmf_causal_task_id", "ah_lmf_causal", ["task_id"], unique=False)
    op.create_index("ix_ah_lmf_causal_node_type", "ah_lmf_causal", ["node_type"], unique=False)

    op.create_table(
        "ah_lmf_wal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("store_tier", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("committed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_wal_committed", "ah_lmf_wal", ["committed"], unique=False)

    op.create_table(
        "ah_lmf_risk_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("action_key", sa.String(length=128), nullable=False),
        sa.Column("base_risk", sa.Integer(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("action_key", name="uq_ah_lmf_risk_profiles_action_key"),
    )

    op.create_table(
        "ah_lmf_risk_profile_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("action_key", sa.String(length=128), nullable=False),
        sa.Column("old_base_risk", sa.Integer(), nullable=False),
        sa.Column("new_base_risk", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_risk_profile_history_action_key", "ah_lmf_risk_profile_history", ["action_key"], unique=False)

    op.create_table(
        "ah_lmf_v6_feedback_signatures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("executor_id", sa.String(length=128), nullable=False),
        sa.Column("error_signature", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_lmf_v6_feedback_signatures_executor_id", "ah_lmf_v6_feedback_signatures", ["executor_id"], unique=False)

    op.create_table(
        "ah_planner_taskgraphs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("graph_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_planner_taskgraphs_goal_id", "ah_planner_taskgraphs", ["goal_id"], unique=False)
    op.create_index("ix_ah_planner_taskgraphs_session_id", "ah_planner_taskgraphs", ["session_id"], unique=False)

    op.create_table(
        "ah_rollout_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("plan_signature", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.String(length=16), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_rollout_metrics_plan_signature", "ah_rollout_metrics", ["plan_signature"], unique=False)

    op.create_table(
        "ah_rollout_policy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("plan_signature", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("plan_signature", name="uq_ah_rollout_policy_plan_signature"),
    )

    op.create_table(
        "ah_projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("goal_statement", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("reject_streak", sa.Integer(), nullable=True),
        sa.Column("metadata_", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name", name="uq_ah_projects_name"),
    )

    op.create_table(
        "ah_drivers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("driver_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_drivers_project_id", "ah_drivers", ["project_id"], unique=False)
    op.create_index("ix_ah_drivers_driver_type", "ah_drivers", ["driver_type"], unique=False)
    op.create_index("ix_ah_drivers_resolved", "ah_drivers", ["resolved"], unique=False)

    op.create_table(
        "ah_sprint_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("week_start", sa.DateTime(), nullable=False),
        sa.Column("goals_json", sa.Text(), nullable=True),
        sa.Column("backlog_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ah_sprint_plans_project_id", "ah_sprint_plans", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ah_sprint_plans_project_id", table_name="ah_sprint_plans")
    op.drop_table("ah_sprint_plans")

    op.drop_index("ix_ah_drivers_resolved", table_name="ah_drivers")
    op.drop_index("ix_ah_drivers_driver_type", table_name="ah_drivers")
    op.drop_index("ix_ah_drivers_project_id", table_name="ah_drivers")
    op.drop_table("ah_drivers")

    op.drop_table("ah_projects")
    op.drop_table("ah_rollout_policy")

    op.drop_index("ix_ah_rollout_metrics_plan_signature", table_name="ah_rollout_metrics")
    op.drop_table("ah_rollout_metrics")

    op.drop_index("ix_ah_planner_taskgraphs_session_id", table_name="ah_planner_taskgraphs")
    op.drop_index("ix_ah_planner_taskgraphs_goal_id", table_name="ah_planner_taskgraphs")
    op.drop_table("ah_planner_taskgraphs")

    op.drop_index("ix_ah_lmf_v6_feedback_signatures_executor_id", table_name="ah_lmf_v6_feedback_signatures")
    op.drop_table("ah_lmf_v6_feedback_signatures")

    op.drop_index("ix_ah_lmf_risk_profile_history_action_key", table_name="ah_lmf_risk_profile_history")
    op.drop_table("ah_lmf_risk_profile_history")

    op.drop_table("ah_lmf_risk_profiles")

    op.drop_index("ix_ah_lmf_wal_committed", table_name="ah_lmf_wal")
    op.drop_table("ah_lmf_wal")

    op.drop_index("ix_ah_lmf_causal_node_type", table_name="ah_lmf_causal")
    op.drop_index("ix_ah_lmf_causal_task_id", table_name="ah_lmf_causal")
    op.drop_index("ix_ah_lmf_causal_parent_id", table_name="ah_lmf_causal")
    op.drop_table("ah_lmf_causal")

    op.drop_index("ix_ah_lmf_working_task_key", table_name="ah_lmf_working")
    op.drop_index("ix_ah_lmf_working_task_id", table_name="ah_lmf_working")
    op.drop_table("ah_lmf_working")

    op.drop_index("ix_ah_lmf_procedural_created_at", table_name="ah_lmf_procedural")
    op.drop_index("ix_ah_lmf_procedural_outcome", table_name="ah_lmf_procedural")
    op.drop_index("ix_ah_lmf_procedural_skill_name", table_name="ah_lmf_procedural")
    op.drop_table("ah_lmf_procedural")

    op.drop_index("ix_ah_lmf_semantic_source", table_name="ah_lmf_semantic")
    op.drop_index("ix_ah_lmf_semantic_concept", table_name="ah_lmf_semantic")
    op.drop_table("ah_lmf_semantic")

    op.drop_index("ix_ah_lmf_episodic_created_at", table_name="ah_lmf_episodic")
    op.drop_index("ix_ah_lmf_episodic_event_type", table_name="ah_lmf_episodic")
    op.drop_index("ix_ah_lmf_episodic_session_id", table_name="ah_lmf_episodic")
    op.drop_index("ix_ah_lmf_episodic_task_id", table_name="ah_lmf_episodic")
    op.drop_table("ah_lmf_episodic")

    op.drop_index("ix_ah_audit_log_created_at", table_name="ah_audit_log")
    op.drop_index("ix_ah_audit_log_decision", table_name="ah_audit_log")
    op.drop_table("ah_audit_log")

    op.drop_index("ix_ah_memory_created_at", table_name="ah_memory")
    op.drop_index("ix_ah_memory_importance", table_name="ah_memory")
    op.drop_index("ix_ah_memory_source", table_name="ah_memory")
    op.drop_table("ah_memory")

    op.drop_index("ix_ah_browser_sessions_task_id", table_name="ah_browser_sessions")
    op.drop_table("ah_browser_sessions")

    op.drop_table("ah_cron_jobs")
    op.drop_table("ah_skills")

    op.drop_index("ix_ah_goals_priority", table_name="ah_goals")
    op.drop_index("ix_ah_goals_status", table_name="ah_goals")
    op.drop_table("ah_goals")

    op.drop_index("ix_ah_agents_session_id", table_name="ah_agents")
    op.drop_table("ah_agents")

    op.drop_index("ix_ah_tasks_created_at", table_name="ah_tasks")
    op.drop_index("ix_ah_tasks_task_type", table_name="ah_tasks")
    op.drop_index("ix_ah_tasks_skill_name", table_name="ah_tasks")
    op.drop_index("ix_ah_tasks_status", table_name="ah_tasks")
    op.drop_index("ix_ah_tasks_session_id", table_name="ah_tasks")
    op.drop_table("ah_tasks")

    op.drop_index("ix_ah_sessions_created_at", table_name="ah_sessions")
    op.drop_index("ix_ah_sessions_status", table_name="ah_sessions")
    op.drop_table("ah_sessions")
