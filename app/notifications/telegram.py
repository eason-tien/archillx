"""
ArcHillx — Telegram Bot Notifier
=================================
配置来源：
  settings.telegram_bot_token   Telegram Bot API Token
  settings.telegram_chat_id     目标 Chat ID（用户、群组或频道）
Feature flag：settings.enable_telegram_notifications

发送格式：Markdown 纯文本。
"""
import logging
from typing import Any, Dict

import httpx

from ..config import settings
from .base import NotifierBase

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0


class TelegramNotifier(NotifierBase):
    """通过 Telegram Bot API 发送通知。"""

    def is_configured(self) -> bool:
        return bool(
            settings.enable_notifications
            and settings.enable_telegram_notifications
            and settings.telegram_bot_token
            and settings.telegram_chat_id
        )

    def send(self, message: str, data: Dict[str, Any] = None) -> bool:
        if not self.is_configured():
            logger.debug("[TelegramNotifier] Not configured — skipping")
            return False

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id":    settings.telegram_chat_id,
            "text":       message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=_TIMEOUT)
            if resp.status_code == 200:
                logger.info("[TelegramNotifier] Message sent successfully")
                return True
            else:
                logger.warning(
                    f"[TelegramNotifier] API returned {resp.status_code}: {resp.text[:200]}"
                )
                return False
        except httpx.TimeoutException:
            logger.warning("[TelegramNotifier] Request timed out")
            return False
        except Exception as exc:
            logger.error(f"[TelegramNotifier] Send failed: {exc}")
            return False
