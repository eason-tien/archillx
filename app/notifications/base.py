"""
ArcHillx — Notifier Base Interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class NotifierBase(ABC):
    """所有通知渠道的基類。"""

    @abstractmethod
    def send(self, message: str, data: Dict[str, Any] = None) -> bool:
        """
        发送通知。
        Returns: True 成功，False 失败。
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """检查渠道所需的配置是否已设置。"""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
