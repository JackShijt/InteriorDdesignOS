"""Design Agent 异常定义（Phase 4）。

复用统一错误体系（agents/orchestrator/error_handler）；
DesignError 作为 Design Agent 顶层异常，便于上层区分来源。
"""
from agents.orchestrator.error_handler import (
    OrchestratorError,
    ValidationError,
    FatalError,
    RecoverableError,
    to_orchestrator_error,
)


class DesignError(OrchestratorError):
    """Design Agent 顶层异常。"""
    category = "DESIGN"


__all__ = [
    "DesignError",
    "ValidationError",
    "FatalError",
    "RecoverableError",
    "OrchestratorError",
    "to_orchestrator_error",
]
