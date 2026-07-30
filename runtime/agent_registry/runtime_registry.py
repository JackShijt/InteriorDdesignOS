"""
runtime.agent_registry.runtime_registry · 运行期 Agent 实例注册表（Phase 3.5 §5）。

统一管理：parser / design / layout / geometry / drawing / validator / repair / export。
- 当前 `parser` 与 `design` 已实现（见 agents/parser、agents/design）。
- 其余保留占位（PlaceholderAgent），不实现任何业务能力（§14 禁止实现）。
- Dispatcher 必须通过本注册表获取 Agent，禁止写死（§4）。

说明（Phase 10）：本文件为“运行期实例注册表”，与 registry.py 中的
“Agent 能力契约注册表（AgentCapabilityRegistry）”职责不同，二者互补：
- runtime_registry：name -> Agent 实例（用于调度执行）
- registry：扫描 agent_contract.json -> 能力契约（用于动态发现 / 路由 / 规划）
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from agents.orchestrator.agent import AgentContext, BaseAgent, Result

PARSER_AGENT = "parser"
DESIGN_AGENT = "design"
PLACEHOLDER_AGENTS = ["layout", "geometry", "drawing", "validator", "repair", "export"]
# Phase 5：8 个 Professional Agent（Mock Logic，禁止 CAD / DWG / 外部 AI）
PROFESSIONAL_AGENTS = [
    "electrical", "plumbing", "lighting", "ceiling",
    "flooring", "hvac", "construction", "furniture",
]


class PlaceholderAgent(BaseAgent):
    """Phase 3.5 §14：其它 Agent 仅保留占位，不实现任何业务逻辑。"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def run(self, context: AgentContext) -> Result:
        return Result(
            success=True,
            output_model={"agent": self.agent_name, "stage": context.stage,
                          "placeholder": True},
            messages=[f"[{self.agent_name}] 占位 Agent（Phase 3.5 未实现）"],
            quality={"confidence": 0.0, "quality_score": 0,
                     "validation_passed": True},
            next_tasks=[],
        )


class AgentRegistry:
    """Phase 3.5 §5：Agent 名称 -> Agent 实例 的统一注册表。"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def names(self) -> List[str]:
        return list(self._agents.keys())

    def build_default(self, workspace_root: Optional[Path] = None,
                      log_dir: Optional[Path] = None) -> "AgentRegistry":
        # parser 与 design 为真实实现；其余为占位（§14 禁止实现下游 Agent）
        from agents.parser.parser import ParserAgent  # 延迟导入，避免循环依赖
        from agents.design.design import DesignAgent
        from professional import build_professional_agents  # Phase 5

        self.register(ParserAgent(workspace_root=workspace_root, log_dir=log_dir))
        self.register(DesignAgent(workspace_root=workspace_root, log_dir=log_dir))
        for name in PLACEHOLDER_AGENTS:
            self.register(PlaceholderAgent(name))
        # Phase 5：注册 8 个 Professional Agent（Mock）
        for agent in build_professional_agents(workspace_root=workspace_root,
                                               log_dir=log_dir):
            self.register(agent)
        return self


def build_runtime_registry(workspace_root: Optional[Path] = None,
                           log_dir: Optional[Path] = None) -> AgentRegistry:
    return AgentRegistry().build_default(workspace_root=workspace_root, log_dir=log_dir)


__all__ = ["PARSER_AGENT", "DESIGN_AGENT", "PLACEHOLDER_AGENTS",
           "PROFESSIONAL_AGENTS", "PlaceholderAgent", "AgentRegistry",
           "build_runtime_registry"]
