"""
ArcHillx v1.0.0 — Skill Manager
本地技能登錄、發現、執行。格式相容 OpenClaw Skill 協議。
"""
from __future__ import annotations

import importlib.util
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import yaml

from ..utils.telemetry import telemetry

logger = logging.getLogger("archillx.skill_manager")


class SkillError(Exception):
    pass


class SkillNotFound(SkillError):
    pass


class SkillValidationError(SkillError):
    pass


class SkillDisabled(SkillError):
    pass


class SkillAccessDenied(SkillError):
    pass


class SkillManager:

    def __init__(self):
        self._local: dict[str, Callable] = {}
        self._manifests: dict[str, dict] = {}

    def startup(self) -> None:
        from ..config import settings
        skills_dir = Path(settings.skills_dir)
        manifest_path = skills_dir / "__manifest__.yaml"
        if manifest_path.exists():
            self._load_from_manifest(manifest_path, skills_dir)
        else:
            self._scan_dir(skills_dir)
        logger.info("SkillManager ready: %d skills", len(self._local))

    def _load_from_manifest(self, path: Path, base: Path) -> None:
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as e:
            logger.error("manifest parse error: %s", e)
            return
        for entry in data.get("skills", []):
            name = entry["name"]
            module_file = base / entry.get("module", f"{name}.py")
            self._load_skill(name, module_file, entry.get("handler", "run"), entry)

    def _scan_dir(self, d: Path) -> None:
        if not d.exists():
            logger.warning("skills_dir not found: %s", d)
            return
        for f in d.glob("*.py"):
            if f.name.startswith("_"):
                continue
            self._load_skill(f.stem, f, "run", {"name": f.stem})

    def _load_skill(self, name: str, path: Path, handler: str, manifest: dict) -> None:
        if not path.exists():
            logger.warning("skill module not found: %s", path)
            return
        try:
            spec = importlib.util.spec_from_file_location(f"archillx.skills.{name}", path)
            if spec is None or spec.loader is None:
                raise SkillError(f"Cannot create import spec for {path}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, handler, None)
            if fn is None:
                logger.warning("skill %s has no '%s' function", name, handler)
                return
            self._local[name] = fn
            self._manifests[name] = manifest
            self._upsert_db(name, manifest)
            logger.info("skill loaded: %s", name)
        except Exception as e:
            logger.exception("skill %s load failed: %s", name, e)

    def _upsert_db(self, name: str, manifest: dict) -> None:
        try:
            from ..db.schema import AHSkill, get_db
            db = next(get_db())
            rec = db.query(AHSkill).filter_by(name=name).first()
            if rec:
                rec.manifest = json.dumps(manifest)
                rec.enabled = manifest.get("enabled", True)
            else:
                db.add(AHSkill(name=name,
                               version=manifest.get("version", "1.0"),
                               description=manifest.get("description", ""),
                               enabled=manifest.get("enabled", True),
                               manifest=json.dumps(manifest)))
            db.commit()
        except Exception as e:
            logger.debug("skill db upsert failed: %s", e)

    def _validate_inputs(self, name: str, inputs: dict | None) -> None:
        from ..config import settings
        if not settings.enable_skill_validation:
            return
        manifest = self._manifests.get(name, {})
        for item in manifest.get("inputs", []):
            if item.get("required") and item.get("name") not in (inputs or {}):
                telemetry.incr("skill_validation_error_total")
                telemetry.incr(f"skill_{name}_validation_error_total")
                raise SkillValidationError(f"Missing required input: {item.get('name')}")

    def _assert_enabled(self, name: str) -> None:
        try:
            from ..db.schema import AHSkill, get_db
            db = next(get_db())
            rec = db.query(AHSkill).filter_by(name=name).first()
            if rec and not rec.enabled:
                telemetry.incr("skill_disabled_total")
                telemetry.incr(f"skill_{name}_disabled_total")
                raise SkillDisabled(f"Skill '{name}' is disabled.")
        except SkillDisabled:
            raise
        except Exception as e:
            logger.debug("skill enabled check skipped for %s: %s", name, e)

    def _authorize(self, name: str, context: dict | None = None) -> None:
        from ..config import settings
        if not settings.enable_skill_acl:
            return
        try:
            from ..security.skill_acl import check_skill_access
            check_skill_access(name, self._manifests.get(name), context)
        except Exception as e:
            telemetry.incr("skill_access_denied_total")
            telemetry.incr(f"skill_{name}_access_denied_total")
            raise SkillAccessDenied(str(e))

    def invoke(self, name: str, inputs: dict | None = None, context: dict | None = None) -> dict:
        telemetry.incr("skill_invoke_total")
        telemetry.incr(f"skill_{name}_invoke_total")
        if name not in self._local:
            telemetry.incr("skill_not_found_total")
            raise SkillNotFound(f"Skill '{name}' not registered.")
        self._assert_enabled(name)
        self._authorize(name, context)
        self._validate_inputs(name, inputs)

        t0 = time.monotonic()
        try:
            result = self._local[name](inputs or {})
            elapsed = round(time.monotonic() - t0, 3)
            self._inc(name, True)
            telemetry.incr("skill_invoke_success_total")
            telemetry.incr(f"skill_{name}_success_total")
            telemetry.timing("skill_invoke", elapsed)
            telemetry.timing(f"skill_{name}_invoke", elapsed)
            response = {"success": True, "output": result, "error": None,
                        "elapsed_s": elapsed}
            if isinstance(result, dict):
                if "error" in result and result.get("error"):
                    response["success"] = False
                    response["error"] = str(result.get("error"))
                    telemetry.incr("skill_invoke_failure_total")
                    telemetry.incr(f"skill_{name}_failure_total")
                if "tokens" in result:
                    response["tokens"] = int(result.get("tokens") or 0)
            return response
        except SkillValidationError:
            self._inc(name, False)
            telemetry.incr("skill_validation_error_total")
            telemetry.incr(f"skill_{name}_validation_error_total")
            raise
        except SkillDisabled:
            self._inc(name, False)
            telemetry.incr("skill_disabled_total")
            telemetry.incr(f"skill_{name}_disabled_total")
            raise
        except SkillAccessDenied:
            self._inc(name, False)
            telemetry.incr("skill_access_denied_total")
            telemetry.incr(f"skill_{name}_access_denied_total")
            raise
        except Exception as e:
            self._inc(name, False)
            telemetry.incr("skill_invoke_failure_total")
            telemetry.incr(f"skill_{name}_failure_total")
            logger.exception("skill %s raised", name)
            return {"success": False, "output": None, "error": str(e),
                    "elapsed_s": round(time.monotonic() - t0, 3)}

    def _inc(self, name: str, ok: bool) -> None:
        try:
            from ..db.schema import AHSkill, get_db
            db = next(get_db())
            r = db.query(AHSkill).filter_by(name=name).first()
            if r:
                r.invoke_count += 1
                if not ok:
                    r.error_count += 1
                db.commit()
        except Exception as e:
            logger.debug("skill counter update failed for %s: %s", name, e)

    def list_skills(self) -> list[dict]:
        return [{"name": n, "manifest": m} for n, m in self._manifests.items()]

    def get_manifest(self, name: str) -> dict | None:
        return self._manifests.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._local

    def register(self, name: str, fn: Callable, manifest: dict | None = None) -> None:
        self._local[name] = fn
        self._manifests[name] = manifest or {"name": name}
        self._upsert_db(name, self._manifests[name])
        logger.info("skill dynamically registered: %s", name)


skill_manager = SkillManager()
