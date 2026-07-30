"""
runtime.agent_registry · Agent 注册表包（Phase 10 §1）。

包含两类互补的注册表：
  - runtime_registry：运行期 Agent 实例注册表（name -> 实例，用于调度执行）。
  - registry        ：Agent 能力契约注册表（扫描 agent_contract.json，用于动态发现）。

为保持向后兼容，历史符号仍从本包顶层导出。
"""
from runtime.agent_registry.runtime_registry import (
    PARSER_AGENT,
    DESIGN_AGENT,
    PLACEHOLDER_AGENTS,
    PROFESSIONAL_AGENTS,
    PlaceholderAgent,
    AgentRegistry,
    build_runtime_registry,
)
from runtime.agent_registry.registry import (
    AgentContract,
    AgentCapabilityRegistry,
    build_capability_registry,
)

__all__ = [
    # 历史（运行期实例注册表）
    "PARSER_AGENT",
    "DESIGN_AGENT",
    "PLACEHOLDER_AGENTS",
    "PROFESSIONAL_AGENTS",
    "PlaceholderAgent",
    "AgentRegistry",
    "build_runtime_registry",
    # Phase 10（能力契约注册表）
    "AgentContract",
    "AgentCapabilityRegistry",
    "build_capability_registry",
]
