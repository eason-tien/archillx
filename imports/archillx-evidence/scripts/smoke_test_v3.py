from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("DB_NAME", "archillx_smoke_v3")
os.environ.setdefault("ARCHILLX_ENABLE_CODE_EXEC", "false")

from app.db.schema import init_db
from app.memory.store import memory_store
from app.runtime.skill_manager import skill_manager, SkillValidationError


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def main() -> None:
    init_db()
    skill_manager.startup()

    # Memory retrieval quality check
    memory_store.add(
        content="FastAPI cron router returns structured API errors with request id",
        source="test",
        tags=["api", "cron"],
        importance=0.6,
        metadata={"case": "api-errors"},
    )
    memory_store.add(
        content="Cron scheduler updates last_run by job name instead of skill name",
        source="test",
        tags=["cron"],
        importance=0.95,
        metadata={"case": "cron-job-name"},
    )
    memory_store.add(
        content="Low priority unrelated memory about image generation",
        source="test",
        tags=["image"],
        importance=0.1,
    )

    results = memory_store.query("cron job name", top_k=2, tags=["cron"], source="test")
    assert_true(len(results) >= 1, "memory query returned no results")
    assert_true(results[0]["metadata"].get("case") == "cron-job-name", "memory ranking did not prioritize strongest cron hit")

    # Skill validation path should remain deterministic
    manifest = {"name": "demo_required", "inputs": [{"name": "text", "required": True}]}
    skill_manager.register("demo_required", lambda data: {"echo": data["text"]}, manifest)

    os.environ["ENABLE_SKILL_VALIDATION"] = "true"
    from app.config import settings
    settings.enable_skill_validation = True

    try:
        skill_manager.invoke("demo_required", {})
        raise AssertionError("expected SkillValidationError was not raised")
    except SkillValidationError:
        pass

    print("OK_SMOKE_V3")


if __name__ == "__main__":
    main()
