"""
InteriorDesignOS · Agent Interface & Result

本模块遵守 PROJECT_RULES.md 的最高约束。

统一 Agent 接口与返回对象（Phase 2 §12、§13）：
- 所有 Agent 统一接口：run(context) -> Result
- 禁止 Agent 之间直接调用；所有调用须经 Dispatcher（PROJECT_RULES §2.3、§4.2）
- Result 统一返回，禁止返回任意 dict：
    success      bool
    output_model dict | None    产出（遵循 schemas/ 的数据对象）
    messages     list[str]       过程信息
    quality      dict | None     质量评估（PROJECT_RULES §18.1）
    next_tasks   list[dict]      后续待建任务建议

本文件同时提供 Phase 2 所需的「虚拟 Agent」：
- StubAgent：占位的虚拟业务 Agent，返回成功 Result（不实现任何装修逻辑）
- AgentRegistry：Agent 注册表，支持按 agent 名称动态获取（PROJECT_RULES §14）

Phase 5.1：接口原语（STAGES / make_metadata / Result / AgentContext / BaseAgent）
已下沉至 core.context.agent_context（依赖规则：Orchestrator 可依赖 core，
Agent 只依赖 core，禁止反向依赖）。本模块保持 re-export 以向后兼容。
"""

from typing import Dict, List, Optional

# Phase 5.1：统一接口原语来自 core 层（此处仅 re-export，保持向后兼容）
from core.context.agent_context import (STAGES, AgentContext, BaseAgent,
                                        Result, make_metadata)


class StubAgent(BaseAgent):
    """虚拟 Agent（Phase 2 §11 调度虚拟 Agent / §14 禁止实现装修逻辑）。

    不实现任何业务；仅返回成功 Result，用于验证调度框架可完整运行。
    """

    def __init__(self, agent_name: str = "stub"):
        self.agent_name = agent_name

    def run(self, context: AgentContext) -> Result:
        meta = make_metadata(
            project_id=context.project_id,
            agent=self.agent_name,
            task_id=context.task_id,
            status="COMPLETED",
        )
        return Result(
            success=True,
            output_model={"metadata": meta, "stage": context.stage,
                          "note": "virtual agent placeholder (Phase 2)"},
            messages=[f"[{self.agent_name}] 虚拟执行阶段 {context.stage} 完成"],
            quality={"confidence": 1.0, "quality_score": 100,
                     "validation_passed": True},
            next_tasks=[],
        )


class AgentRegistry:
    """Agent 注册表（PROJECT_RULES §14 动态调度）。"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def names(self) -> List[str]:
        return list(self._agents.keys())

    def build_default(self) -> "AgentRegistry":
        """注册覆盖 12 阶段的全量虚拟 Agent（每个阶段一个 stub）。"""
        for stage in STAGES:
            self.register(StubAgent(agent_name=stage.lower()))
        return self


__all__ = [
    "STAGES", "make_metadata", "Result", "AgentContext", "BaseAgent",
    "StubAgent", "AgentRegistry",
]
