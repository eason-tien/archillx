"""
ArcHillx — Generic HTTP Webhook Notifier
=========================================
配置来源：
  settings.notification_webhook_url   目标 Webhook URL（支持任何 HTTP POST 接收端）
Feature flag：settings.enable_webhook_notifications

JSON 格式：
  {
    "event_type": "RISK_HIGH",
    "message":    "...(格式化报告)...",
    "data":       {...原始数据...},
    "timestamp":  "2026-02-21T10:00:00Z"
  }

适配目标：
  * n8n / Make（前 Integromat）— 触发自动化工作流
  * 企业微信 / 钉钉 / Feishu 群机器人（设置对应 Webhook URL）
  * 自建日志系统
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

from ..config import settings
from .base import NotifierBase

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0


class WebhookNotifier(NotifierBase):
    """通用 HTTP Webhook 通知渠道。"""

    def is_configured(self) -> bool:
        return bool(
            settings.enable_notifications
            and settings.enable_webhook_notifications
            and settings.notification_webhook_url
        )

    def send(self, message: str, data: Dict[str, Any] = None) -> bool:
        if not self.is_configured():
            logger.debug("[WebhookNotifier] Not configured — skipping")
            return False

        body = {
            "event_type": (data or {}).get("_event_type", "UNKNOWN"),
            "message":    message,
            "data":       {k: v for k, v in (data or {}).items() if not k.startswith("_")},
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        headers = {"Content-Type": "application/json; charset=utf-8"}

        try:
            resp = httpx.post(
                settings.notification_webhook_url,
                content=body_bytes,
                headers=headers,
                timeout=_TIMEOUT,
            )
            if resp.status_code < 400:
                logger.info(f"[WebhookNotifier] Delivered (HTTP {resp.status_code})")
                return True
            else:
                logger.warning(f"[WebhookNotifier] HTTP {resp.status_code}: {resp.text[:200]}")
                return False
        except httpx.TimeoutException:
            logger.warning("[WebhookNotifier] Request timed out")
            return False
        except Exception as exc:
            logger.error(f"[WebhookNotifier] Send failed: {exc}")
            return False
