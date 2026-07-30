"""
InteriorDesignOS · Parser Agent Exceptions（Phase 3 §12）

复用 orchestrator 的统一异常体系（orchestrator 为 L0 接口层，Agent 实现其接口）：
- RecoverableError：可恢复（如临时 IO 不可用），可重试
- ValidationError：Schema 校验失败 / 输入不合规范（立即中止，不可重试）
- FatalError：致命错误（不可重试）

禁止 print() / sys.exit()（§12）。异常通过 Result 或向上抛出统一处理。
"""

from agents.orchestrator.error_handler import (
    OrchestratorError,
    RecoverableError,
    FatalError,
    ValidationError,
    to_orchestrator_error,
    is_recoverable,
)

__all__ = [
    "OrchestratorError",
    "RecoverableError",
    "FatalError",
    "ValidationError",
    "to_orchestrator_error",
    "is_recoverable",
]
