"""
agents.orchestrator.orchestrator_agent · Orchestrator Agent（Phase 10 §3）。

职责：
    - 分析目标（ProjectRequirement）
    - 创建任务（调用 Dynamic Task Planner 生成 TaskGraph）
    - 调度 Agent（提供可执行任务查询）
    - 处理失败 / 触发恢复

禁止：
    直接生成任何业务模型（只做“编排 / 计划 / 调度”，产出 TaskGraph 计划，不产出 LayoutModel 等）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.context import AgentContext, BaseAgent, Result
from agents.orchestrator.task_graph import TaskGraph
from runtime.agent_registry.registry import AgentCapabilityRegistry
from runtime.orchestrator.task_planner import ProjectRequirement, TaskPlanner


class OrchestratorAgent(BaseAgent):
    """智能编排 Agent：把“项目需求”转化为可执行的“任务图”，并负责调度与恢复。"""

    agent_name = "orchestrator"
    version = "1.0"

    def __init__(self, registry: Optional[AgentCapabilityRegistry] = None):
        self.registry = registry or AgentCapabilityRegistry()
        self.planner = TaskPlanner(registry=self.registry)

    def capabilities(self) -> List[str]:
        return ["orchestration", "task_planning", "scheduling", "recovery"]

    # ---- 统一入口 ----
    def run(self, context: AgentContext) -> Result:
        try:
            requirement = self._requirement_from_context(context)
            analysis = self.analyze_goal(requirement)
            task_graph = self.create_task_graph(requirement)
            plan = [
                {
                    "task_id": t.task_id,
                    "agent": t.agent,
                    "stage": t.stage,
                    "dependencies": t.dependencies,
                    "output_schema": t.parameters.get("output_schema", []),
                }
                for t in task_graph.all_tasks()
            ]
            return Result(
                success=True,
                output_model={
                    "kind": "OrchestrationPlan",
                    "requirement": requirement.to_dict(),
                    "analysis": analysis,
                    "task_graph": task_graph.to_dict(),
                    "plan": plan,
                },
                messages=[f"Orchestrator: 生成 {len(plan)} 个任务"],
            )
        except Exception as exc:  # noqa: BLE001
            return Result(success=False, messages=[f"OrchestratorAgent 失败：{exc}"])

    # ---- 分析目标 ----
    def analyze_goal(self, requirement: ProjectRequirement) -> Dict[str, Any]:
        """分析需求，识别可用输入、目标产物与需覆盖的专业。"""
        needed_producers = []
        for schema in requirement.target_schemas:
            producers = self.registry.find_agent_by_output(schema)
            needed_producers.extend(p.agent_name for p in producers)
        return {
            "goal": requirement.goal,
            "initial_schemas": list(requirement.initial_schemas),
            "target_schemas": list(requirement.target_schemas),
            "disciplines": list(requirement.disciplines),
            "target_producers": list(dict.fromkeys(needed_producers)),
        }

    # ---- 创建任务 ----
    def create_task_graph(self, requirement: ProjectRequirement) -> TaskGraph:
        return self.planner.plan(requirement)

    # ---- 完整 E2E 任务图（Phase 11 §2：Orchestrator 真正接管流程） ----
    def build_full_graph(self, requirement: ProjectRequirement) -> TaskGraph:
        """构建从 Input 到 Deliverable 的完整任务图（不硬编码 Agent 顺序）。

        流程：parser -> design -> layout -> [专业 Agent 并行] -> geometry
              -> drawing -> validator -> deliverable。
        专业 Agent 通过能力注册表自动发现，仅纳入需求 disciplines 中且具备 impl 的契约。
        """
        tg = TaskGraph()
        wanted = {d.lower() for d in requirement.disciplines}

        tg.create_task(
            "parser_task", "parser", "ORIGINAL_MODEL", status="READY",
            parameters={"output_schema": ["OriginalModel"]})
        tg.create_task(
            "design_task", "design", "DESIGN_SPEC",
            dependencies=["parser_task"], status="READY",
            parameters={"output_schema": ["DesignSpec"]})
        tg.create_task(
            "layout_task", "layout", "LAYOUT",
            dependencies=["design_task"], status="READY",
            parameters={"output_schema": ["LayoutModel"]})

        # 自动发现专业 Agent（禁止硬编码）
        prof_contracts = [
            c for c in self.registry.find_agent_by_capability("professional_deepening")
            if ((c.discipline or c.agent_name).lower() in wanted)
            and c.impl
        ]
        prof_task_ids: List[str] = []
        for c in prof_contracts:
            tid = f"{c.agent_name}_task"
            tg.create_task(
                tid, c.agent_name, "PROFESSIONAL_DEEPENING",
                dependencies=["layout_task"], status="READY",
                parameters={
                    "output_schema": list(c.output_schema),
                    "discipline": c.discipline,
                    "impl": c.impl,
                })
            prof_task_ids.append(tid)

        tg.create_task(
            "geometry_task", "geometry", "GEOMETRY",
            dependencies=["layout_task"], status="READY",
            parameters={"output_schema": ["GeometryModel"]})
        tg.create_task(
            "drawing_task", "drawing", "DRAWING",
            dependencies=["geometry_task"], status="READY",
            parameters={"output_schema": ["DrawingModel", "DWG"]})
        tg.create_task(
            "validator_task", "validator", "VALIDATION",
            dependencies=["layout_task", "drawing_task"] + prof_task_ids,
            status="READY",
            parameters={"output_schema": ["ValidationReport"]})
        tg.create_task(
            "deliverable_task", "deliverable", "EXPORT",
            dependencies=["validator_task"], status="READY",
            parameters={"output_schema": ["Deliverable"]})
        return tg

    # ---- 调度 ----
    def next_runnable(self, task_graph: TaskGraph) -> List[str]:
        return [t.task_id for t in task_graph.get_runnable()]

    # ---- 失败处理 / 恢复 ----
    def handle_failure(self, task_graph: TaskGraph, task_id: str,
                       error: str, max_retries: int = 1) -> Dict[str, Any]:
        """记录失败并决定恢复策略（重试 / 放弃）。"""
        task = task_graph.get_task(task_id)
        if task is None:
            return {"action": "unknown_task", "task_id": task_id}
        retries = int(task.parameters.get("_retries", 0))
        if retries < max_retries:
            task.parameters["_retries"] = retries + 1
            task.notes = f"failure: {error}"
            return {"action": "retry", "task_id": task_id,
                    "retry": retries + 1}
        task_graph.reset_status(task_id, "FAILED")
        return {"action": "abort", "task_id": task_id, "error": error}

    def trigger_recovery(self, task_graph: TaskGraph, task_id: str) -> str:
        """把任务重置为可执行状态，供断点恢复重新调度。"""
        task_graph.reset_status(task_id, "READY")
        return task_id

    # ---- 内部 ----
    def _requirement_from_context(self, context: AgentContext) -> ProjectRequirement:
        data = context.inputs.get("requirement") or context.inputs.get("project_requirement")
        if isinstance(data, ProjectRequirement):
            return data
        if isinstance(data, dict):
            req = ProjectRequirement.from_dict(data)
        else:
            req = ProjectRequirement(project_id=context.project_id)
        if not req.project_id:
            req.project_id = context.project_id
        return req


__all__ = ["OrchestratorAgent"]
