"""
runtime.registry · Agent 能力注册表统一入口（Phase 11 §3）。

Phase 11 要求检查 `runtime/registry` 与 `agents/*/agent_contract.json`：
所有 Agent 必须自动发现、注册、校验契约、获取输入/输出 Schema。

本包仅做转发，真正的实现位于 `runtime.agent_registry.registry`
（扫描 `agents/*/agent_contract.json`，禁止硬编码 Agent）。
"""
from typing import Dict, List

from runtime.agent_registry.registry import (
    AgentCapabilityRegistry,
    AgentContract,
    build_capability_registry,
)

# 便捷单例：导入即自动扫描 agents/*/agent_contract.json
default_registry = build_capability_registry()


def validate_all() -> Dict[str, List[str]]:
    """校验全部契约，返回 {agent_name: [错误]}。"""
    return default_registry.validate_contracts()


__all__ = [
    "AgentCapabilityRegistry",
    "AgentContract",
    "build_capability_registry",
    "default_registry",
    "validate_all",
]
