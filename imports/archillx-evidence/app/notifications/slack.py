"""
ArcHillx — Slack Incoming Webhook Notifier
==========================================
配置来源：settings.slack_webhook_url
Feature flag：settings.enable_slack_notifications

报告以带颜色的 Attachment 格式发送（红/橙/绿 对应风险等级）。
"""
import logging
from typing import Any, Dict

import httpx

from ..config import settings
from .base import NotifierBase

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0

# 颜色映射
_EVENT_COLORS = {
    "RISK_CRITICAL":   "#cc0000",
    "RISK_HIGH":       "#ff6600",
    "BLOCK":           "#cc0000",
    "CONSENSUS_VETO":  "#cc0000",
    "DRIFT_ALERT":     "#ff9900",
    "RL_ESCALATE":     "#ff9900",
    "TASK_COMPLETE":   "#36a64f",
}


class SlackNotifier(NotifierBase):
    """通过 Slack Incoming Webhook 发送通知。"""

    def is_configured(self) -> bool:
        return bool(
            settings.enable_notifications
            and settings.enable_slack_notifications
            and settings.slack_webhook_url
        )

    def send(self, message: str, data: Dict[str, Any] = None) -> bool:
        if not self.is_configured():
            logger.debug("[SlackNotifier] Not configured — skipping")
            return False

        event_type = (data or {}).get("_event_type", "")
        color      = _EVENT_COLORS.get(event_type, "#439fe0")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "text":  message,
                    "footer": "ArcHillx Autonomous Agent",
                    "mrkdwn_in": ["text"],
                }
            ]
        }

        try:
            resp = httpx.post(settings.slack_webhook_url, json=payload, timeout=_TIMEOUT)
            if resp.status_code == 200:
                logger.info("[SlackNotifier] Message sent successfully")
                return True
            else:
                logger.warning(f"[SlackNotifier] API returned {resp.status_code}: {resp.text[:200]}")
                return False
        except httpx.TimeoutException:
            logger.warning("[SlackNotifier] Request timed out")
            return False
        except Exception as exc:
            logger.error(f"[SlackNotifier] Send failed: {exc}")
            return False
