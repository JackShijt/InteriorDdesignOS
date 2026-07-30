"""
InteriorDesignOS · Session

本模块遵守 PROJECT_RULES.md 的最高约束。

Session 聚合一次运行所需的运行时组件（Phase 2 §2）：
- ProjectRuntime（工程状态）
- EventBus（事件）
- UnifiedLogger（日志）
- ContextManager（上下文读写，由 orchestrator 注入）

Session 是「无业务」的胶水层，仅负责装配与对外暴露统一接口。
"""

from typing import Optional

from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.project_runtime import ProjectRuntime


class Session:
    """单次运行的会话装配体。"""

    def __init__(self, logger: Optional[UnifiedLogger] = None,
                 event_bus: Optional[EventBus] = None,
                 project_runtime: Optional[ProjectRuntime] = None,
                 context_manager: Optional[object] = None):
        self.logger = logger or UnifiedLogger()
        self.event_bus = event_bus or EventBus(self.logger)
        self.project_runtime = project_runtime or ProjectRuntime()
        # context_manager 由 orchestrator 注入（依赖 schemas/，置于代理层）
        self.context_manager = context_manager

    def attach_context_manager(self, context_manager: object) -> None:
        self.context_manager = context_manager
