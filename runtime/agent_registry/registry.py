"""
runtime.agent_registry.registry · Agent Capability Registry（Phase 10 §1）。

职责：
  自动扫描 `agents/*/agent_contract.json`，构建“Agent 能力契约”注册表，
  为动态编排（TaskPlanner / SchemaRouter / Orchestrator）提供发现与匹配能力。

读取字段（对齐历史契约字段名，做兼容映射）：
  - agent_name          （或历史字段 name）
  - capabilities
  - input_schema
  - output_schema
  - dependencies        （历史契约可能缺省 -> []）
  - forbidden_actions   （或历史字段 forbidden）

提供查询：
  - find_agent_by_input(schema)
  - find_agent_by_output(schema)
  - find_agent_by_capability(capability)
  - list_agents()

禁止：
  在代码中硬编码任何 Agent（全部来自 agent_contract.json 扫描）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# runtime/agent_registry/registry.py -> parents[2] == 仓库根
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_AGENTS_DIR = _REPO_ROOT / "agents"


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


@dataclass
class AgentContract:
    """单个 Agent 的能力契约（从 agent_contract.json 归一化而来）。"""

    agent_name: str
    capabilities: List[str] = field(default_factory=list)
    input_schema: List[str] = field(default_factory=list)
    output_schema: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    role: str = ""
    discipline: Optional[str] = None
    impl: Optional[str] = None
    source: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    # ---- 查询辅助 ----
    def accepts(self, schema: str) -> bool:
        return schema in self.input_schema

    def produces(self, schema: str) -> bool:
        return schema in self.output_schema

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "capabilities": list(self.capabilities),
            "input_schema": list(self.input_schema),
            "output_schema": list(self.output_schema),
            "dependencies": list(self.dependencies),
            "forbidden_actions": list(self.forbidden_actions),
            "role": self.role,
            "discipline": self.discipline,
            "impl": self.impl,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any],
                  source: Optional[str] = None) -> "AgentContract":
        name = data.get("agent_name") or data.get("name")
        if not name:
            raise ValueError("agent_contract 缺少 agent_name/name 字段")
        return cls(
            agent_name=str(name),
            capabilities=_as_list(data.get("capabilities")),
            input_schema=_as_list(data.get("input_schema")),
            output_schema=_as_list(data.get("output_schema")),
            dependencies=_as_list(data.get("dependencies")),
            forbidden_actions=_as_list(
                data.get("forbidden_actions", data.get("forbidden"))),
            role=str(data.get("role", "")),
            discipline=data.get("discipline"),
            impl=data.get("impl"),
            source=source,
            raw=dict(data),
        )


class AgentCapabilityRegistry:
    """扫描 agent_contract.json 并提供能力查询的注册表（禁止硬编码 Agent）。"""

    def __init__(self, agents_dir: Optional[Path] = None, auto_load: bool = True):
        self.agents_dir = Path(agents_dir) if agents_dir else _DEFAULT_AGENTS_DIR
        self._contracts: Dict[str, AgentContract] = {}
        self._errors: List[str] = []
        if auto_load:
            self.reload()

    # ---- 扫描 ----
    def reload(self) -> "AgentCapabilityRegistry":
        self._contracts.clear()
        self._errors.clear()
        if not self.agents_dir.exists():
            return self
        for contract_path in sorted(self.agents_dir.glob("*/agent_contract.json")):
            try:
                data = json.loads(contract_path.read_text(encoding="utf-8"))
                contract = AgentContract.from_dict(
                    data, source=str(contract_path))
                self._contracts[contract.agent_name] = contract
            except Exception as exc:  # noqa: BLE001
                self._errors.append(f"{contract_path}: {exc}")
        return self

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    # ---- 基础访问 ----
    def list_agents(self) -> List[AgentContract]:
        return list(self._contracts.values())

    def names(self) -> List[str]:
        return list(self._contracts.keys())

    def get(self, agent_name: str) -> Optional[AgentContract]:
        return self._contracts.get(agent_name)

    def __len__(self) -> int:
        return len(self._contracts)

    def __contains__(self, agent_name: str) -> bool:
        return agent_name in self._contracts

    # ---- 能力查询 ----
    def find_agent_by_input(self, schema: str) -> List[AgentContract]:
        """返回所有能够“消费” schema 的 Agent。"""
        return [c for c in self._contracts.values() if c.accepts(schema)]

    def find_agent_by_output(self, schema: str) -> List[AgentContract]:
        """返回所有能够“产出” schema 的 Agent。"""
        return [c for c in self._contracts.values() if c.produces(schema)]

    def find_agent_by_capability(self, capability: str) -> List[AgentContract]:
        """返回所有具备指定 capability 的 Agent。"""
        return [c for c in self._contracts.values()
                if c.has_capability(capability)]

    # ---- 契约注册 / Schema 查询（Phase 11 §3） ----
    def register(self, contract: AgentContract) -> "AgentCapabilityRegistry":
        """运行时注册一个契约（例如测试注入或动态契约）。"""
        self._contracts[contract.agent_name] = contract
        return self

    def get_input_schema(self, agent_name: str) -> List[str]:
        """获取某 Agent 的输入 Schema（Phase 11 §3）。"""
        c = self.get(agent_name)
        return list(c.input_schema) if c else []

    def get_output_schema(self, agent_name: str) -> List[str]:
        """获取某 Agent 的输出 Schema（Phase 11 §3）。"""
        c = self.get(agent_name)
        return list(c.output_schema) if c else []

    def validate_contracts(self) -> Dict[str, List[str]]:
        """校验所有已加载契约的完整性（Phase 11 §3）。

        返回 {agent_name: [错误描述, ...]}；空 dict 表示全部通过。
        校验项：
          - agent_name 非空
          - capabilities 非空
          - input_schema / output_schema 为 list
          - 至少声明一个 output_schema（否则无法形成数据流）
        """
        report: Dict[str, List[str]] = {}
        for name, c in self._contracts.items():
            problems: List[str] = []
            if not c.agent_name:
                problems.append("缺少 agent_name")
            if not c.capabilities:
                problems.append("capabilities 为空")
            if not isinstance(c.input_schema, list):
                problems.append("input_schema 非 list")
            if not isinstance(c.output_schema, list):
                problems.append("output_schema 非 list")
            if isinstance(c.output_schema, list) and not c.output_schema:
                problems.append("未声明任何 output_schema（无法形成数据流）")
            if problems:
                report[name] = problems
        return report

    # ---- 聚合视图 ----
    def all_input_schemas(self) -> List[str]:
        out: List[str] = []
        for c in self._contracts.values():
            out.extend(c.input_schema)
        return sorted(set(out))

    def all_output_schemas(self) -> List[str]:
        out: List[str] = []
        for c in self._contracts.values():
            out.extend(c.output_schema)
        return sorted(set(out))

    def all_capabilities(self) -> List[str]:
        out: List[str] = []
        for c in self._contracts.values():
            out.extend(c.capabilities)
        return sorted(set(out))

    def to_dict(self) -> Dict[str, Any]:
        return {name: c.to_dict() for name, c in self._contracts.items()}


def build_capability_registry(
        agents_dir: Optional[Path] = None) -> AgentCapabilityRegistry:
    return AgentCapabilityRegistry(agents_dir=agents_dir)


__all__ = ["AgentContract", "AgentCapabilityRegistry", "build_capability_registry"]
