"""
InteriorDesignOS · AgentContext / Result / BaseAgent（Phase 5.1 §3）

统一 Agent 接口原语下沉到 core 层：
- Agent 只依赖 core（禁止依赖 runtime / orchestrator）
- Orchestrator 从本模块 re-export，保持向后兼容
- 所有数据流通过 Context（输入）与 Artifact（输出）管理

Result 契约（Phase 2 §13，保持不变）：
    success      bool
    output_model dict | None
    messages     list[str]
    quality      dict | None
    next_tasks   list[dict]
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 阶段序列（与 schemas 枚举一致）
STAGES = [
    "INITIALIZATION", "INPUT_ANALYSIS", "ORIGINAL_MODEL", "DESIGN_SPEC",
    "LAYOUT", "PROFESSIONAL_DEEPENING", "GEOMETRY", "DRAWING",
    "DWG_GENERATION", "VALIDATION", "REPAIR", "EXPORT",
]


def make_metadata(project_id: str, agent: str, task_id: str, status: str,
                  quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造统一元数据（PROJECT_RULES §4.3、§18.1）。"""
    return {
        "project_id": project_id,
        "agent": agent,
        "task_id": task_id,
        "timestamp": datetime.now().astimezone().isoformat(),
        "schema_version": "1.0",
        "status": status,
        "quality": quality or {"confidence": 1.0, "quality_score": 100,
                               "validation_passed": True},
    }


@dataclass
class Result:
    """Agent 统一返回对象。禁止返回裸 dict。"""
    success: bool
    output_model: Optional[Dict[str, Any]] = None
    messages: List[str] = field(default_factory=list)
    quality: Optional[Dict[str, Any]] = None
    next_tasks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output_model": self.output_model,
            "messages": self.messages,
            "quality": self.quality,
            "next_tasks": self.next_tasks,
        }


@dataclass
class AgentContext:
    """传给 Agent.run 的上下文（Phase 5.1 §3）。

    Agent 所需的全部数据通过本对象传入：
    - project_id / task_id / stage / agent_name：任务定位
    - workspace：项目工作区根（Path，由 Runtime 注入；Agent 不得自行推断）
    - inputs：输入模型 / 输入引用（如 {"layout": {...}} 或 {"layout_path": "..."}）
    - outputs：受控输出槽（由框架回填，Agent 不直接写文件）
    - metadata：附加元数据
    兼容字段（Phase 2 起已有调用方）：
    - context_manager / logger / event_bus / extra / input_refs / parameters
    """
    project_id: str
    task_id: str
    stage: str = "PROFESSIONAL_DEEPENING"
    agent_name: str = ""
    workspace: Optional[Path] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # ---- 兼容字段（Dispatcher / 既有测试仍在使用）----
    context_manager: Any = None
    logger: Any = None
    event_bus: Any = None
    extra: Dict[str, Any] = field(default_factory=dict)
    input_refs: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """所有 Agent 的抽象基类（统一接口：run(context) -> Result）。"""
    agent_name: str = "base"
    version: str = "1.0"

    @abstractmethod
    def run(self, context: AgentContext) -> Result:
        """执行任务，返回统一 Result。"""
        raise NotImplementedError

    def capabilities(self) -> List[str]:
        return []

    def descriptor(self) -> Dict[str, Any]:
        """能力声明（PROJECT_RULES §14.1）。"""
        return {
            "agent": self.agent_name,
            "version": self.version,
            "capabilities": self.capabilities(),
        }


__all__ = ["STAGES", "make_metadata", "Result", "AgentContext", "BaseAgent"]
