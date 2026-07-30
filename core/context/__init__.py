"""core.context · Agent 上下文与统一接口（Phase 5.1 §3）。"""
from core.context.agent_context import (STAGES, AgentContext, BaseAgent,
                                        Result, make_metadata)

__all__ = ["STAGES", "AgentContext", "BaseAgent", "Result", "make_metadata"]
