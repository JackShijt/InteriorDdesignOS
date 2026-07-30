"""
InteriorDesignOS · Orchestrator Agent Package

本包遵守 PROJECT_RULES.md 的最高约束。

Orchestrator 是控制核心（L0 流程控制层，PROJECT_RULES §2.1）：
- 调度框架（不含装修算法 / CAD / LLM，Phase 2 §14）
- 统一 Agent 接口、Task Graph、状态机、事件总线、检查点

导出关键类型供上层使用。
"""

from agents.orchestrator.error_handler import (
    OrchestratorError, RecoverableError, FatalError, ValidationError,
)
from agents.orchestrator.task_graph import Task, TaskGraph, TaskStateMachine, TaskStatus
from agents.orchestrator.agent import (
    Result, AgentContext, BaseAgent, StubAgent, AgentRegistry, make_metadata,
)
from agents.orchestrator.state_manager import StateManager
from agents.orchestrator.context_manager import ContextManager
from agents.orchestrator.checkpoint import Checkpoint
from agents.orchestrator.scheduler import Scheduler
from agents.orchestrator.dispatcher import Dispatcher
from agents.orchestrator.orchestrator import Orchestrator

__all__ = [
    "OrchestratorError", "RecoverableError", "FatalError", "ValidationError",
    "Task", "TaskGraph", "TaskStateMachine", "TaskStatus",
    "Result", "AgentContext", "BaseAgent", "StubAgent", "AgentRegistry", "make_metadata",
    "StateManager", "ContextManager", "Checkpoint", "Scheduler", "Dispatcher",
    "Orchestrator",
]
