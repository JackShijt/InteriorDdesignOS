"""
InteriorDesignOS · Error Handler

本模块遵守 PROJECT_RULES.md 的最高约束。

统一异常处理（Phase 2 §11 / PROJECT_RULES §9）：
- 所有异常统一归为三类：
    RecoverableError  可重试（超时 / 临时不可用 / IO 冲突）
    FatalError        不可重试（逻辑 / 配置 / 未知）
    ValidationError   数据 / Schema 校验失败（不可重试，立即中止）
- 禁止 print()；禁止直接 sys.exit()（由上层决策）。
- to_orchestrator_error(exc) 将任意异常归一为上述三类之一。
"""

import asyncio


class OrchestratorError(Exception):
    """所有编排层异常的基类。"""
    category = "ORCHESTRATOR"


class RecoverableError(OrchestratorError):
    """可重试错误（PROJECT_RULES §9.2）。"""
    category = "RECOVERABLE"


class FatalError(OrchestratorError):
    """不可重试错误（PROJECT_RULES §9.3）。"""
    category = "FATAL"


class ValidationError(OrchestratorError):
    """数据 / Schema 校验失败（PROJECT_RULES §6.3）。"""
    category = "VALIDATION"


# 视作「可重试」的内建异常类型
_RECOVERABLE_BUILTINS = (
    TimeoutError,
    ConnectionError,
    OSError,
    BlockingIOError,
    asyncio.TimeoutError,
)


def to_orchestrator_error(exc: Exception) -> OrchestratorError:
    """将任意异常归一为三类 OrchestratorError 之一。"""
    if isinstance(exc, OrchestratorError):
        return exc
    if isinstance(exc, _RECOVERABLE_BUILTINS):
        return RecoverableError(f"{type(exc).__name__}: {exc}")
    # 其余一律视为 Fatal
    return FatalError(f"{type(exc).__name__}: {exc}")


def is_recoverable(exc: Exception) -> bool:
    return isinstance(to_orchestrator_error(exc), RecoverableError)


__all__ = [
    "OrchestratorError",
    "RecoverableError",
    "FatalError",
    "ValidationError",
    "to_orchestrator_error",
    "is_recoverable",
]
