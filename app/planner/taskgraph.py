"""
ArcHillx v1.0.0 — TaskGraph Data Structures
==============================================
Goal-driven planner intermediate representation. Auditable and replayable.

Hierarchy:
  Goal          Top-level goal (user intent)
  └─ SubGoal    Decomposed sub-goal (recursive)
     └─ Action  Atomic execution step

Each node has:
  - id           Globally unique UUID
  - status       PENDING | IN_PROGRESS | DONE | FAILED | SKIPPED
  - depends_on   Dependency node id list (DAG)
  - produces     Produced resource id list
  - requires     Required resource id list (preconditions)

Full TaskGraph can be serialized to JSON for API return and storage.

Standalone — no external MGIS dependencies.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ──────────────────────────────────────────────────────────────────────

class NodeStatus(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE        = "DONE"
    FAILED      = "FAILED"
    SKIPPED     = "SKIPPED"


class ResourceKind(str, Enum):
    TOOL        = "TOOL"          # Executable tool / API
    MATERIAL    = "MATERIAL"      # Raw material / data
    CAPABILITY  = "CAPABILITY"    # Abstract capability (e.g. "carpentry")
    ARTIFACT    = "ARTIFACT"      # Generated artifact
    UNKNOWN     = "UNKNOWN"


# ── Resource node ──────────────────────────────────────────────────────────────

@dataclass
class Resource:
    """Represents a resource in the planning flow (tool, material, capability, or artifact)."""
    name:       str
    kind:       ResourceKind                  = ResourceKind.UNKNOWN
    source:     Optional[str]                 = None   # local / network / generate
    available:  bool                          = False
    metadata:   Dict[str, Any]                = field(default_factory=dict)
    resource_id: str                          = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name":       self.name,
            "kind":       self.kind.value,
            "source":     self.source,
            "available":  self.available,
            "metadata":   self.metadata,
        }


# ── Action node ────────────────────────────────────────────────────────────────

@dataclass
class Action:
    """
    Atomic execution step.

    executor_id:  Agent/Tool ID responsible for this action
    tool_name:    Tool name (corresponds to ResourceRegistry)
    payload:      Input params for the executor
    result:       Execution output (filled by PlannerLoop)
    audit_id:     Audit id returned by governor after audit
    """
    name:        str
    executor_id: str                          = "default_executor"
    tool_name:   Optional[str]                = None
    payload:     Dict[str, Any]               = field(default_factory=dict)
    depends_on:  List[str]                    = field(default_factory=list)
    produces:    List[str]                    = field(default_factory=list)   # resource_id list
    requires:    List[str]                    = field(default_factory=list)   # resource_id list
    status:      NodeStatus                   = NodeStatus.PENDING
    result:      Optional[Dict[str, Any]]     = None
    audit_id:    Optional[str]                = None
    error_msg:   Optional[str]                = None
    action_id:   str                          = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:  str                          = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id":   self.action_id,
            "name":        self.name,
            "executor_id": self.executor_id,
            "tool_name":   self.tool_name,
            "payload":     self.payload,
            "depends_on":  self.depends_on,
            "produces":    self.produces,
            "requires":    self.requires,
            "status":      self.status.value,
            "result":      self.result,
            "audit_id":    self.audit_id,
            "error_msg":   self.error_msg,
            "created_at":  self.created_at,
        }


# ── SubGoal node ───────────────────────────────────────────────────────────────

@dataclass
class SubGoal:
    """
    Sub-goal: decomposes a Goal into independently completable sub-tasks.
    Contains actions and optional nested sub-goals.
    """
    name:        str
    description: str                          = ""
    actions:     List[Action]                 = field(default_factory=list)
    sub_goals:   List["SubGoal"]              = field(default_factory=list)
    depends_on:  List[str]                    = field(default_factory=list)
    produces:    List[str]                    = field(default_factory=list)
    requires:    List[str]                    = field(default_factory=list)
    status:      NodeStatus                   = NodeStatus.PENDING
    subgoal_id:  str                          = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def is_complete(self) -> bool:
        return all(
            a.status in (NodeStatus.DONE, NodeStatus.SKIPPED)
            for a in self.actions
        ) and all(sg.is_complete for sg in self.sub_goals)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgoal_id":  self.subgoal_id,
            "name":        self.name,
            "description": self.description,
            "depends_on":  self.depends_on,
            "produces":    self.produces,
            "requires":    self.requires,
            "status":      self.status.value,
            "actions":     [a.to_dict() for a in self.actions],
            "sub_goals":   [sg.to_dict() for sg in self.sub_goals],
        }


# ── Goal root node ─────────────────────────────────────────────────────────────

@dataclass
class Goal:
    """
    Top-level goal. Root node of TaskGraph.

    goal_text:    Original natural language goal (user input or inferred)
    confidence:   Confidence from GoalInference
    trigger:      Trigger source (user_explicit / inferred / signal_review)
    """
    goal_text:   str
    confidence:  float                        = 1.0
    trigger:     str                          = "user_explicit"
    sub_goals:   List[SubGoal]                = field(default_factory=list)
    resources:   List[Resource]               = field(default_factory=list)
    status:      NodeStatus                   = NodeStatus.PENDING
    goal_id:     str                          = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:  str                          = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_complete(self) -> bool:
        return all(sg.is_complete for sg in self.sub_goals)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id":    self.goal_id,
            "goal_text":  self.goal_text,
            "confidence": self.confidence,
            "trigger":    self.trigger,
            "status":     self.status.value,
            "created_at": self.created_at,
            "sub_goals":  [sg.to_dict() for sg in self.sub_goals],
            "resources":  [r.to_dict() for r in self.resources],
        }


# ── TaskGraph top-level container ──────────────────────────────────────────────

@dataclass
class TaskGraph:
    """
    Complete task execution graph.

    Created and continuously updated by PlannerLoop.
    Serializable via to_dict() / from_dict() for API return,
    database storage, and cross-session recovery.
    """
    task_id:          str
    goal:             Goal
    execution_trace:  List[Dict[str, Any]]    = field(default_factory=list)
    step_fail_count:  int                     = 0
    plan_fail_count:  int                     = 0
    goal_fail_count:  int                     = 0
    solution_sigs:    List[str]               = field(default_factory=list)
    created_at:       str                     = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at:       str                     = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_trace(self, event_type: str, **kwargs: Any) -> None:
        """Append an execution trace record."""
        self.execution_trace.append({
            "ts":         datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **kwargs,
        })
        self.touch()

    def next_pending_action(self) -> Optional[Action]:
        """Return next executable Action in topological order (dependencies satisfied, status PENDING)."""
        done_ids = self._collect_done_action_ids()
        for sg in self.goal.sub_goals:
            act = self._find_action_in_subgoal(sg, done_ids)
            if act:
                return act
        return None

    def _collect_done_action_ids(self) -> set:
        result: set = set()
        for sg in self.goal.sub_goals:
            self._collect_from_subgoal(sg, result)
        return result

    def _collect_from_subgoal(self, sg: SubGoal, result: set) -> None:
        for a in sg.actions:
            if a.status in (NodeStatus.DONE, NodeStatus.SKIPPED):
                result.add(a.action_id)
        for child in sg.sub_goals:
            self._collect_from_subgoal(child, result)

    def _find_action_in_subgoal(self, sg: SubGoal, done_ids: set) -> Optional[Action]:
        for a in sg.actions:
            if (
                a.status == NodeStatus.PENDING
                and all(dep in done_ids for dep in a.depends_on)
            ):
                return a
        for child in sg.sub_goals:
            act = self._find_action_in_subgoal(child, done_ids)
            if act:
                return act
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":         self.task_id,
            "goal":            self.goal.to_dict(),
            "execution_trace": self.execution_trace,
            "step_fail_count": self.step_fail_count,
            "plan_fail_count": self.plan_fail_count,
            "goal_fail_count": self.goal_fail_count,
            "solution_sigs":   self.solution_sigs,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskGraph":
        """Restore from dict (for API storage recovery)."""
        goal_data = data["goal"]
        resources = [
            Resource(
                name=r["name"],
                kind=ResourceKind(r.get("kind", "UNKNOWN")),
                source=r.get("source"),
                available=r.get("available", False),
                metadata=r.get("metadata", {}),
                resource_id=r["resource_id"],
            )
            for r in goal_data.get("resources", [])
        ]
        sub_goals = [cls._sg_from_dict(sg) for sg in goal_data.get("sub_goals", [])]
        goal = Goal(
            goal_text=goal_data["goal_text"],
            confidence=goal_data.get("confidence", 1.0),
            trigger=goal_data.get("trigger", "user_explicit"),
            sub_goals=sub_goals,
            resources=resources,
            status=NodeStatus(goal_data.get("status", "PENDING")),
            goal_id=goal_data["goal_id"],
            created_at=goal_data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )
        return cls(
            task_id=data["task_id"],
            goal=goal,
            execution_trace=data.get("execution_trace", []),
            step_fail_count=data.get("step_fail_count", 0),
            plan_fail_count=data.get("plan_fail_count", 0),
            goal_fail_count=data.get("goal_fail_count", 0),
            solution_sigs=data.get("solution_sigs", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    @staticmethod
    def _sg_from_dict(data: Dict[str, Any]) -> SubGoal:
        actions = [
            Action(
                name=a["name"],
                executor_id=a.get("executor_id", "default_executor"),
                tool_name=a.get("tool_name"),
                payload=a.get("payload", {}),
                depends_on=a.get("depends_on", []),
                produces=a.get("produces", []),
                requires=a.get("requires", []),
                status=NodeStatus(a.get("status", "PENDING")),
                result=a.get("result"),
                audit_id=a.get("audit_id"),
                error_msg=a.get("error_msg"),
                action_id=a["action_id"],
                created_at=a.get("created_at", datetime.now(timezone.utc).isoformat()),
            )
            for a in data.get("actions", [])
        ]
        sub_goals = [TaskGraph._sg_from_dict(sg) for sg in data.get("sub_goals", [])]
        return SubGoal(
            name=data["name"],
            description=data.get("description", ""),
            actions=actions,
            sub_goals=sub_goals,
            depends_on=data.get("depends_on", []),
            produces=data.get("produces", []),
            requires=data.get("requires", []),
            status=NodeStatus(data.get("status", "PENDING")),
            subgoal_id=data["subgoal_id"],
        )


# ══════════════════════════════════════════════════════════════════════════════
#  TaskGraph Planner  — DB-backed facade
# ══════════════════════════════════════════════════════════════════════════════

import json as _json
import logging as _logging

_logger = _logging.getLogger(__name__)


class _TaskGraphPlanner:
    """
    Persist and manage TaskGraph plans in the database.

    create_plan   → build an empty TaskGraph and save it
    list_plans    → query ah_planner_taskgraphs
    get_plan      → restore a single plan as a dict
    execute_plan  → set plan status to running (actual execution is handled by main loop)
    """

    def create_plan(
        self,
        *,
        title: str,
        goal_id: Optional[int] = None,
        session_id: Optional[int] = None,
        constraints: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        from ..db.schema import SessionLocal, AHPlannerTaskGraph

        # Build a minimal TaskGraph
        goal = Goal(
            goal_text=title,
            trigger="user_explicit",
        )
        tg = TaskGraph(task_id=str(uuid.uuid4()), goal=goal)
        graph_json = _json.dumps(tg.to_dict())

        db = SessionLocal()
        try:
            row = AHPlannerTaskGraph(
                goal_id=goal_id,
                session_id=session_id,
                title=title,
                status="pending",
                graph_json=graph_json,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            _logger.info("[Planner] Created plan '%s' (id=%d)", title, row.id)
            return {
                "plan_id": row.id,
                "task_id": tg.task_id,
                "title": title,
                "status": "pending",
                "created_at": row.created_at.isoformat(),
            }
        finally:
            db.close()

    def list_plans(
        self, *, status: str = "pending", limit: int = 20
    ) -> List[Dict[str, Any]]:
        from ..db.schema import SessionLocal, AHPlannerTaskGraph
        from sqlalchemy import desc
        db = SessionLocal()
        try:
            query = (
                db.query(AHPlannerTaskGraph)
                .order_by(desc(AHPlannerTaskGraph.created_at))
            )
            if status != "all":
                query = query.filter(AHPlannerTaskGraph.status == status)
            rows = query.limit(limit).all()
            return [
                {
                    "plan_id": r.id,
                    "title": r.title,
                    "status": r.status,
                    "goal_id": r.goal_id,
                    "session_id": r.session_id,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        from ..db.schema import SessionLocal, AHPlannerTaskGraph
        db = SessionLocal()
        try:
            row = db.query(AHPlannerTaskGraph).filter(AHPlannerTaskGraph.id == plan_id).first()
            if not row:
                return None
            graph = _json.loads(row.graph_json) if row.graph_json else {}
            return {
                "plan_id": row.id,
                "title": row.title,
                "status": row.status,
                "goal_id": row.goal_id,
                "session_id": row.session_id,
                "graph": graph,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
        finally:
            db.close()

    def execute_plan(self, plan_id: int) -> Dict[str, Any]:
        from ..db.schema import SessionLocal, AHPlannerTaskGraph
        db = SessionLocal()
        try:
            row = db.query(AHPlannerTaskGraph).filter(AHPlannerTaskGraph.id == plan_id).first()
            if not row:
                return {"status": "error", "detail": "Plan not found"}
            if row.status not in ("pending", "failed"):
                return {"status": "skipped", "detail": f"Plan is already {row.status}"}
            row.status = "running"
            db.commit()
            _logger.info("[Planner] Plan %d set to running", plan_id)
            return {"status": "running", "plan_id": plan_id}
        finally:
            db.close()


# ── Singleton ────────────────────────────────────────────────────────────────
task_graph_planner = _TaskGraphPlanner()
