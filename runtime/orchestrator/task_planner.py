"""
runtime.orchestrator.task_planner · Dynamic Task Planner（Phase 10 §2）。

输入：ProjectRequirement
输出：TaskGraph

规划方式（数据流驱动，禁止硬编码 Agent 调用顺序）：
    输入数据(schema) → 用能力注册表匹配可消费的 Agent → 生成任务
    Agent 的产出 schema 又成为新的可用输入，如此循环直到目标 schema 全部可产出。

例如（initial=[DesignSpec], target=[DrawingModel, ValidationReport]）自动生成：
    layout_task → professional_tasks(并行) → geometry_task → drawing_task → validation_task

禁止：AI 设计算法 / 施工规范知识库 / 真实装修算法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agents.orchestrator.task_graph import TaskGraph
from runtime.agent_registry.registry import AgentCapabilityRegistry, AgentContract

# 聚合型输入 schema（一个逻辑名代表“任意/全部专业模型”）
AGGREGATE_SCHEMAS = {"ProfessionalModels", "ProfessionalModel"}
PROFESSIONAL_CAPABILITY = "professional_deepening"

# schema -> 阶段（仅用于标注，不参与调度顺序决策）
_SCHEMA_STAGE = {
    "LayoutModel": "LAYOUT",
    "GeometryModel": "GEOMETRY",
    "DrawingModel": "DRAWING",
    "DWG": "DRAWING",
    "ValidationReport": "VALIDATION",
    "OriginalModel": "ORIGINAL_MODEL",
    "DesignSpec": "DESIGN_SPEC",
}

_DEFAULT_DISCIPLINES = ["electrical", "lighting", "plumbing", "ceiling"]


@dataclass
class ProjectRequirement:
    """一个项目需求：描述“已有什么数据”“想要什么产物”，而非“先调用谁”。"""

    project_id: str
    name: str = "orchestrated-project"
    goal: str = "full_drawing"
    initial_schemas: List[str] = field(default_factory=lambda: ["DesignSpec"])
    target_schemas: List[str] = field(
        default_factory=lambda: ["DrawingModel", "ValidationReport"])
    disciplines: List[str] = field(
        default_factory=lambda: list(_DEFAULT_DISCIPLINES))
    inputs: Dict[str, Any] = field(default_factory=dict)
    # ---- E2E 结构化需求（供 Mock 上游构造器使用，非 Schema Contract） ----
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    area: Optional[float] = None
    story: int = 1
    style: str = ""
    features: List[str] = field(default_factory=list)
    materials: Dict[str, str] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectRequirement":
        return cls(
            project_id=data.get("project_id", "proj"),
            name=data.get("name", "orchestrated-project"),
            goal=data.get("goal", "full_drawing"),
            initial_schemas=list(data.get("initial_schemas", ["DesignSpec"])),
            target_schemas=list(data.get(
                "target_schemas", ["DrawingModel", "ValidationReport"])),
            disciplines=list(data.get("disciplines", list(_DEFAULT_DISCIPLINES))),
            inputs=dict(data.get("inputs", {})),
            rooms=list(data.get("rooms", [])),
            area=data.get("area"),
            story=int(data.get("story", 1) or 1),
            style=data.get("style", ""),
            features=list(data.get("features", [])),
            materials=dict(data.get("materials", {})),
            source=data.get("source", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "goal": self.goal,
            "initial_schemas": list(self.initial_schemas),
            "target_schemas": list(self.target_schemas),
            "disciplines": list(self.disciplines),
            "rooms": list(self.rooms),
            "area": self.area,
            "story": self.story,
            "style": self.style,
            "features": list(self.features),
            "materials": dict(self.materials),
            "source": self.source,
        }


@dataclass
class _PlannedTask:
    task_id: str
    agent: str
    stage: str
    deps: List[str]
    input_schema: List[str]
    output_schema: List[str]
    capabilities: List[str]
    impl: Optional[str]
    discipline: Optional[str]


class TaskPlanner:
    """动态任务规划器：ProjectRequirement -> TaskGraph。"""

    def __init__(self, registry: Optional[AgentCapabilityRegistry] = None):
        self.registry = registry or AgentCapabilityRegistry()

    # ---- 主入口 ----
    def plan(self, requirement: ProjectRequirement) -> TaskGraph:
        planned = self.plan_tasks(requirement)
        return self._build_graph(planned)

    def plan_tasks(self, requirement: ProjectRequirement) -> List[_PlannedTask]:
        contracts = self.registry.list_agents()

        # 专业 Agent 的产出 schema 集合（用于聚合匹配 ProfessionalModels）
        prof_contracts = [c for c in contracts
                          if c.has_capability(PROFESSIONAL_CAPABILITY)]
        prof_schemas = set()
        for c in prof_contracts:
            prof_schemas.update(c.output_schema)

        # 可产出 schema 全集（用于判断某输入是否“可选”）
        producible = set(requirement.initial_schemas)
        for c in contracts:
            producible.update(c.output_schema)

        # 需求过滤：仅纳入被请求的专业
        wanted = {d.lower() for d in requirement.disciplines}
        candidates: List[AgentContract] = []
        for c in contracts:
            if c.has_capability(PROFESSIONAL_CAPABILITY):
                disc = (c.discipline or c.agent_name).lower()
                if disc not in wanted and c.agent_name.lower() not in wanted:
                    continue
            candidates.append(c)

        available = set(requirement.initial_schemas)
        produced_by: Dict[str, Optional[str]] = {
            s: None for s in requirement.initial_schemas}
        placed: Dict[str, str] = {}
        planned: List[_PlannedTask] = []

        changed = True
        while changed:
            changed = False
            for c in candidates:
                if c.agent_name in placed:
                    continue
                # 产出已全部可用 -> 无需再生产（避免 design/parser 重复生产 initial）
                if c.output_schema and all(o in available for o in c.output_schema):
                    continue
                ok, deps = self._match_inputs(
                    c, available, produced_by, prof_schemas, producible)
                if not ok:
                    continue
                task_id = f"{c.agent_name}_task"
                stage = self._stage_for(c)
                planned.append(_PlannedTask(
                    task_id=task_id, agent=c.agent_name, stage=stage,
                    deps=deps, input_schema=list(c.input_schema),
                    output_schema=list(c.output_schema),
                    capabilities=list(c.capabilities),
                    impl=c.impl, discipline=c.discipline))
                placed[c.agent_name] = task_id
                for o in c.output_schema:
                    available.add(o)
                    produced_by.setdefault(o, task_id)
                changed = True

        # 目标裁剪：只保留产出目标 schema 所必需的任务
        planned = self._prune_to_targets(planned, requirement.target_schemas)
        return planned

    # ---- 输入匹配（Schema 驱动）----
    def _match_inputs(self, contract: AgentContract, available: set,
                      produced_by: Dict[str, Optional[str]],
                      prof_schemas: set,
                      producible: set) -> Tuple[bool, List[str]]:
        deps: List[str] = []
        real_match = False
        for schema in contract.input_schema:
            if schema in available:
                real_match = True
                pt = produced_by.get(schema)
                if pt:
                    deps.append(pt)
            elif schema in AGGREGATE_SCHEMAS:
                avail_prof = [s for s in prof_schemas if s in available]
                if not avail_prof:
                    return False, []
                real_match = True
                for s in avail_prof:
                    pt = produced_by.get(s)
                    if pt:
                        deps.append(pt)
            elif schema not in producible:
                # 无人产出且非初始输入 -> 视为可选，跳过
                continue
            else:
                # 可被产出但当前尚不可用 -> 需等待
                return False, []
        if not real_match:
            return False, []
        # 去重且保持顺序
        return True, list(dict.fromkeys(deps))

    def _stage_for(self, contract: AgentContract) -> str:
        for schema in contract.output_schema:
            if schema in _SCHEMA_STAGE:
                return _SCHEMA_STAGE[schema]
        if contract.has_capability(PROFESSIONAL_CAPABILITY):
            return "PROFESSIONAL_DEEPENING"
        return "PROFESSIONAL_DEEPENING"

    def _prune_to_targets(self, planned: List[_PlannedTask],
                          targets: List[str]) -> List[_PlannedTask]:
        if not planned:
            return planned
        by_id = {p.task_id: p for p in planned}
        target_set = set(targets)
        seeds = [p.task_id for p in planned
                 if target_set & set(p.output_schema)]
        if not seeds:
            # 目标不可达 -> 保留全部（避免产出空图）
            return planned
        keep = set()
        stack = list(seeds)
        while stack:
            tid = stack.pop()
            if tid in keep:
                continue
            keep.add(tid)
            for dep in by_id[tid].deps:
                if dep in by_id:
                    stack.append(dep)
        # 保留原有放置顺序（拓扑序）
        return [p for p in planned if p.task_id in keep]

    def _build_graph(self, planned: List[_PlannedTask]) -> TaskGraph:
        tg = TaskGraph()
        kept_ids = {p.task_id for p in planned}
        for p in planned:
            deps = [d for d in p.deps if d in kept_ids]
            tg.create_task(
                p.task_id, agent=p.agent, stage=p.stage,
                dependencies=deps, status="READY",
                input_refs=list(p.input_schema),
                parameters={
                    "output_schema": list(p.output_schema),
                    "capabilities": list(p.capabilities),
                    "impl": p.impl,
                    "discipline": p.discipline,
                })
        return tg


__all__ = ["ProjectRequirement", "TaskPlanner"]
