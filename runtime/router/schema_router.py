"""
runtime.router.schema_router · Schema Router（Phase 10 §4）。

功能：
    根据 input_schema / output_schema，寻找 Producer Agent -> Consumer Agent，
    形成自动数据流（Producer 的 output 恰好是 Consumer 的 input）。

对外能力：
    - find_producer(schema)      产出该 schema 的 Agent
    - find_consumer(schema)      消费该 schema 的 Agent
    - route(agent_name)          某 Agent 产出后，下一步可流向的 Consumer
    - build_flow(initial)        由初始 schema 出发展开完整数据流边集
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from runtime.agent_registry.registry import AgentCapabilityRegistry, AgentContract

# 聚合 schema：任意专业模型都可满足
_AGGREGATE = {"ProfessionalModels", "ProfessionalModel"}
_PROFESSIONAL_CAPABILITY = "professional_deepening"


@dataclass(frozen=True)
class DataFlowEdge:
    """一条数据流边：producer --schema--> consumer。"""
    producer: str
    consumer: str
    schema: str

    def to_dict(self) -> Dict[str, str]:
        return {"producer": self.producer, "consumer": self.consumer,
                "schema": self.schema}


class SchemaRouter:
    """基于契约 input/output schema 的自动数据流路由器。"""

    def __init__(self, registry: Optional[AgentCapabilityRegistry] = None):
        self.registry = registry or AgentCapabilityRegistry()
        self._prof_schemas: Set[str] = set()
        for c in self.registry.find_agent_by_capability(_PROFESSIONAL_CAPABILITY):
            self._prof_schemas.update(c.output_schema)

    # ---- 生产者 / 消费者 ----
    def find_producer(self, schema: str) -> List[AgentContract]:
        return self.registry.find_agent_by_output(schema)

    def find_consumer(self, schema: str) -> List[AgentContract]:
        consumers = list(self.registry.find_agent_by_input(schema))
        # 若该 schema 属专业模型，则消费 ProfessionalModels 聚合的 Agent 也算消费者
        if schema in self._prof_schemas:
            for c in self.registry.list_agents():
                if any(s in _AGGREGATE for s in c.input_schema) \
                        and c not in consumers:
                    consumers.append(c)
        return consumers

    def route(self, agent_name: str) -> List[AgentContract]:
        """返回某 Agent 产出后，可直接接收其产物的下游 Agent。"""
        producer = self.registry.get(agent_name)
        if producer is None:
            return []
        downstream: List[AgentContract] = []
        seen: Set[str] = set()
        for schema in producer.output_schema:
            for consumer in self.find_consumer(schema):
                if consumer.agent_name == agent_name:
                    continue
                if consumer.agent_name not in seen:
                    seen.add(consumer.agent_name)
                    downstream.append(consumer)
        return downstream

    def build_flow(self, initial_schemas: List[str]) -> List[DataFlowEdge]:
        """由初始 schema 出发，逐步展开可达的数据流边集合。"""
        available: Set[str] = set(initial_schemas)
        placed: Set[str] = set()
        edges: List[DataFlowEdge] = []
        producible = set(initial_schemas)
        for c in self.registry.list_agents():
            producible.update(c.output_schema)

        changed = True
        while changed:
            changed = False
            for c in self.registry.list_agents():
                if c.agent_name in placed:
                    continue
                if c.output_schema and all(o in available for o in c.output_schema):
                    continue
                if not self._inputs_ready(c, available, producible):
                    continue
                # 记录数据流边
                for schema in c.input_schema:
                    for prod in self._producers_of(schema, available):
                        edges.append(DataFlowEdge(prod, c.agent_name, schema))
                placed.add(c.agent_name)
                available.update(c.output_schema)
                changed = True
        return edges

    # ---- 内部 ----
    def _inputs_ready(self, contract: AgentContract, available: Set[str],
                      producible: Set[str]) -> bool:
        real = False
        for schema in contract.input_schema:
            if schema in available:
                real = True
            elif schema in _AGGREGATE:
                if any(s in available for s in self._prof_schemas):
                    real = True
                else:
                    return False
            elif schema not in producible:
                continue  # 可选
            else:
                return False
        return real

    def _producers_of(self, schema: str, available: Set[str]) -> List[str]:
        if schema in _AGGREGATE:
            out = []
            for s in self._prof_schemas:
                if s in available:
                    out.extend(p.agent_name for p in self.find_producer(s))
            return list(dict.fromkeys(out))
        return [p.agent_name for p in self.find_producer(schema)]


__all__ = ["SchemaRouter", "DataFlowEdge"]
