"""
ArcHillx — Notifications Dispatcher
=====================================
Central dispatch for all notification channels.

Channels (individually feature-gated):
  slack      → SlackNotifier    (ENABLE_SLACK_NOTIFICATIONS=true)
  telegram   → TelegramNotifier (ENABLE_TELEGRAM_NOTIFICATIONS=true)
  webhook    → WebhookNotifier  (ENABLE_WEBHOOK_NOTIFICATIONS=true)
  websocket  → ws_broadcaster   (ENABLE_WEBSOCKET_NOTIFICATIONS=true)

Master gate: ENABLE_NOTIFICATIONS=true
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def dispatch_notification(
    *,
    message: str,
    channel: str = "all",
    level: str = "info",
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Send a notification to one or all configured channels.

    Args:
        message:  Human-readable notification body.
        channel:  "all" | "slack" | "telegram" | "webhook" | "websocket"
        level:    "info" | "warning" | "error" | "success"
        metadata: Additional key/value data attached to the notification.

    Returns:
        Dict with per-channel send results.
    """
    from ..config import settings
    if not settings.enable_notifications:
        return {"status": "disabled", "detail": "ENABLE_NOTIFICATIONS=false"}

    data = {"_event_type": f"NOTIFY_{level.upper()}", **(metadata or {})}
    results: Dict[str, Any] = {}

    def _should(ch: str) -> bool:
        return channel in ("all", ch)

    # ── Slack ──────────────────────────────────────────────────────────────
    if _should("slack") and settings.enable_slack_notifications:
        try:
            from .slack import SlackNotifier
            notifier = SlackNotifier()
            results["slack"] = {"sent": notifier.send(message, data)}
        except Exception as e:
            logger.warning("Slack dispatch error: %s", e)
            results["slack"] = {"sent": False, "error": str(e)}

    # ── Telegram ───────────────────────────────────────────────────────────
    if _should("telegram") and settings.enable_telegram_notifications:
        try:
            from .telegram import TelegramNotifier
            notifier = TelegramNotifier()
            results["telegram"] = {"sent": notifier.send(message, data)}
        except Exception as e:
            logger.warning("Telegram dispatch error: %s", e)
            results["telegram"] = {"sent": False, "error": str(e)}

    # ── Webhook ────────────────────────────────────────────────────────────
    if _should("webhook") and settings.enable_webhook_notifications:
        try:
            from .webhook import WebhookNotifier
            notifier = WebhookNotifier()
            results["webhook"] = {"sent": notifier.send(message, data)}
        except Exception as e:
            logger.warning("Webhook dispatch error: %s", e)
            results["webhook"] = {"sent": False, "error": str(e)}

    # ── WebSocket broadcast (fire-and-forget via sync wrapper) ─────────────
    if _should("websocket") and settings.enable_websocket_notifications:
        try:
            import asyncio
            from .ws_broadcaster import broadcaster
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            if loop and loop.is_running():
                asyncio.ensure_future(
                    broadcaster.broadcast(
                        event_type=f"NOTIFY_{level.upper()}",
                        data=data,
                        formatted_message=message,
                    )
                )
            else:
                asyncio.run(
                    broadcaster.broadcast(
                        event_type=f"NOTIFY_{level.upper()}",
                        data=data,
                        formatted_message=message,
                    )
                )
            results["websocket"] = {"sent": True}
        except Exception as e:
            logger.warning("WebSocket dispatch error: %s", e)
            results["websocket"] = {"sent": False, "error": str(e)}

    if not results:
        return {
            "status": "no_channels",
            "detail": "No notification channels are enabled for the requested channel.",
        }

    return {"status": "dispatched", "results": results}


def get_notification_status() -> Dict[str, Any]:
    """Return which notification channels are configured and active."""
    from ..config import settings
    from .slack import SlackNotifier
    from .telegram import TelegramNotifier
    from .webhook import WebhookNotifier
    from .ws_broadcaster import broadcaster

    return {
        "enabled": settings.enable_notifications,
        "channels": {
            "slack": {
                "enabled": settings.enable_slack_notifications,
                "configured": SlackNotifier().is_configured(),
            },
            "telegram": {
                "enabled": settings.enable_telegram_notifications,
                "configured": TelegramNotifier().is_configured(),
            },
            "webhook": {
                "enabled": settings.enable_webhook_notifications,
                "configured": WebhookNotifier().is_configured(),
            },
            "websocket": {
                "enabled": settings.enable_websocket_notifications,
                "active_connections": broadcaster.status()["active_connections"],
            },
        },
    }
