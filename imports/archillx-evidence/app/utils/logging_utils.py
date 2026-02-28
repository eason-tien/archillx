from __future__ import annotations

import contextvars
import json
import logging
from typing import Any

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("session_id", default=None)
_task_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("task_id", default=None)


def set_request_context(request_id: str | None = None, session_id: str | None = None, task_id: str | None = None):
    tokens = {}
    if request_id is not None:
        tokens["request_id"] = _request_id_var.set(str(request_id))
    if session_id is not None:
        tokens["session_id"] = _session_id_var.set(str(session_id))
    if task_id is not None:
        tokens["task_id"] = _task_id_var.set(str(task_id))
    return tokens


def clear_request_context(tokens: dict[str, Any]) -> None:
    if not tokens:
        return
    if "request_id" in tokens:
        _request_id_var.reset(tokens["request_id"])
    if "session_id" in tokens:
        _session_id_var.reset(tokens["session_id"])
    if "task_id" in tokens:
        _task_id_var.reset(tokens["task_id"])


def get_request_context() -> dict[str, str | None]:
    return {
        "request_id": _request_id_var.get(),
        "session_id": _session_id_var.get(),
        "task_id": _task_id_var.get(),
    }


def bind_runtime_context(*, session_id: Any = None, task_id: Any = None) -> None:
    if session_id is not None:
        _session_id_var.set(str(session_id))
    if task_id is not None:
        _task_id_var.set(str(task_id))


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_request_context()
        record.request_id = ctx.get("request_id") or "-"
        record.session_id = ctx.get("session_id") or "-"
        record.task_id = ctx.get("task_id") or "-"
        return True


def configure_logging(level_name: str = "INFO") -> None:
    root = logging.getLogger()
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format=(
                "%(asctime)s %(levelname)s %(name)s "
                "[request_id=%(request_id)s session_id=%(session_id)s task_id=%(task_id)s] — %(message)s"
            ),
        )
    root.setLevel(level)
    for handler in root.handlers:
        exists = any(isinstance(f, RequestContextFilter) for f in handler.filters)
        if not exists:
            handler.addFilter(RequestContextFilter())


def structured_log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
