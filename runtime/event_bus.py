"""
InteriorDesignOS · Event Bus

本模块遵守 PROJECT_RULES.md 的最高约束。

发布 / 订阅事件总线（Phase 2 §9）：
- subscribe(event_type, handler)
- publish(event)
- 支持按 EventType 过滤订阅。
- handler 异常被捕获并转为 error 日志，禁止向上抛出导致流程中断（PROJECT_RULES §9.1）。
"""

from typing import Callable, Dict, List

from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType

# 处理者签名：Callable[[Event], None]
EventHandler = Callable[[Event], None]


class EventBus:
    """进程内发布/订阅事件总线。"""

    def __init__(self, logger: UnifiedLogger):
        self._logger = logger
        self._subs: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subs.setdefault(event_type, []).append(handler)

    def publish(self, event: Event) -> None:
        handlers = list(self._subs.get(event.type, []))
        for h in handlers:
            try:
                h(event)
            except Exception as e:  # 禁止事件处理者中断主流程
                self._logger.error(
                    "event_handler_failed",
                    error=e,
                    event_type=event.type.value,
                )

    def clear(self) -> None:
        self._subs.clear()
