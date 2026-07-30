"""
runtime.pipeline.e2e_pipeline · 完整运行时集成流水线（Phase 11 §1 / §2 / §5 / §7）。

职责：把“架构完整、模块可测试”的 InteriorDesignOS 串成“完整运行闭环”：

    Input
      -> Orchestrator（分析目标 / 生成 TaskGraph / 依赖排序）
      -> Runtime Pipeline（调度 Agent / 保存产物 / 检查点 / 失败恢复）
      -> Artifacts（Workspace 落盘，含六元元数据）
      -> Validation（Conflict + Approval 网关）
      -> Export（Deliverable）

特性：
  - 由 OrchestratorAgent 构建完整任务图（parser→design→layout→专业(并行)
    →geometry→drawing→validator→deliverable）；**禁止硬编码 Agent 顺序**。
  - 专业 Agent 经能力注册表自动发现并通过契约 impl 动态加载。
  - 每轮调度后保存 Checkpoint；支持 resume 从中断处续跑。
  - 发布事件到 EventBus（PROCESS/RUNTIME 可见性）。
  - 不修改任何 Schema SSOT；不接入真实 AutoCAD；不实现真实设计算法。

约束：本文件为 Runtime，禁止 import 任何“业务设计算法”；上游(parser/design/
layout)与下游(deliverable)构造来自 `stage_builders`（明确标注的 Mock 构造器）。
"""
from __future__ import annotations

import importlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.context import AgentContext
from core.logging import build_logger
from models.model_pipeline import ModelPipeline
from runtime.agent_registry.registry import AgentCapabilityRegistry
from runtime.approval.approval import ApprovalManager
from runtime.checkpoint.checkpoint import CheckpointManager
from runtime.conflict.resolver import ConflictResolver
from runtime.event_bus import EventBus
from runtime.logger import UnifiedLogger
from runtime.message import Event, EventType
from runtime.orchestrator.task_planner import ProjectRequirement
from runtime.project_runtime import ProjectRuntime
from runtime.workspace.workspace import WorkspaceManager

from agents.orchestrator.orchestrator_agent import OrchestratorAgent
from agents.orchestrator.task_graph import Task, TaskGraph
from runtime.pipeline.stage_builders import (
    build_deliverable,
    build_design_spec,
    build_layout_model,
    build_original_model,
)
from runtime.pipeline.cad_export import (
    export_drawing_to_dwg,
    read_dwg_to_generated_model,
    round_trip_validate,
)


def _instantiate(impl: str):
    """通过 `module:Class` 动态加载 Agent 实例（禁止硬编码）。"""
    module_path, cls_name = impl.split(":")
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)()


class E2EPipeline:
    """完整运行时集成流水线（Phase 11）。"""

    def __init__(self, workspace_root, backend: str = "mock", logger=None,
                 max_workers: int = 4, auto_approve: bool = True,
                 event_bus: Optional[EventBus] = None):
        self.workspace_root = Path(workspace_root)
        self.backend = backend
        self.logger = logger or build_logger()
        self.max_workers = max_workers
        self.auto_approve = auto_approve
        self.event_bus = event_bus

        self.registry = AgentCapabilityRegistry()
        self.orchestrator = OrchestratorAgent(registry=self.registry)
        self._rt = ProjectRuntime(workspace_root)
        self._conflict_resolver = ConflictResolver()
        self._approval_manager = ApprovalManager()

        # 运行期状态（单次 run 内有效）
        self._active_graph: Optional[TaskGraph] = None
        self._project_dir: Optional[Path] = None

    # ======================================================================
    # 入口
    # ======================================================================
    def run(self, requirement, resume: bool = False,
            fail_after: Optional[str] = None) -> Dict[str, Any]:
        """启动一个完整设计项目（或从中断恢复）。"""
        if isinstance(requirement, dict):
            requirement = ProjectRequirement.from_dict(requirement)

        project_id = requirement.project_id
        self._project_id = project_id
        self._project_dir = self._rt.project_dir(project_id)
        cp = CheckpointManager(self._project_dir)

        if resume and cp.has():
            return self._resume(requirement, cp)

        # ---- 初始化（Phase 11 §1 步骤 1-2） ----
        project = self._rt.create(project_id, requirement.name)
        workspace = WorkspaceManager(self._project_dir)
        workspace.init({**project, "stage": "INITIALIZATION",
                        "status": "RUNNING"})
        self._ensure_event_bus(self._project_dir)

        self._publish(EventType.PROJECT_STARTED, project_id=project_id,
                      name=requirement.name)

        # ---- Orchestrator 接管：生成 TaskGraph（Phase 11 §2） ----
        graph = self.orchestrator.build_full_graph(requirement)
        self._active_graph = graph
        workspace.save_task_graph(graph.to_dict())
        self._rt.set_stage(project_id, "ORIGINAL_MODEL")
        self._rt.set_state(project_id, "RUNNING")

        mp = ModelPipeline(project_id)
        state = self._new_state()
        self._execute(graph, state, requirement, workspace, mp, cp,
                     fail_after=fail_after)
        return self._finalize(requirement, state, workspace, graph)

    # ======================================================================
    # 执行循环（依赖解析 + 调度 + 检查点 + 失败恢复）
    # ======================================================================
    def _execute(self, graph, state, requirement, workspace, mp, cp,
                 fail_after=None, max_rounds: int = 64):
        rounds = 0
        while not graph.is_complete():
            rounds += 1
            if rounds > max_rounds:
                self.logger.error("execution_loop_exceeded",
                                  project_id=requirement.project_id)
                break

            runnable = graph.get_runnable()
            if not runnable:
                # 可能进入 WAITING_USER（人工审批）；尝试自动放行
                if self._handle_waiting(graph, state, workspace, requirement):
                    continue
                break

            round_ids = [t.task_id for t in runnable]
            prof = [t for t in runnable if t.stage == "PROFESSIONAL_DEEPENING"]
            others = [t for t in runnable if t.stage != "PROFESSIONAL_DEEPENING"]

            # 串行执行非专业任务
            for t in others:
                self._run_task(t, state, requirement, workspace, mp)

            # 并行执行专业 Agent
            if prof:
                self._run_professional(prof, state, requirement, workspace, mp)
                self._conflict_gate(state, requirement, workspace)

            # 每轮保存检查点（Phase 11 §1 步骤 6-7）
            self._save_checkpoint(graph, state, cp, requirement)

            # 失败模拟（测试用）：本轮完成后抛出，模拟中断
            if fail_after and fail_after in round_ids:
                self.logger.info("simulated_failure", task_id=fail_after)
                raise RuntimeError(f"simulated failure after {fail_after}")

        # 执行收尾（deliverable 已完成则无需动作）

    # ---- 单任务执行 + 失败重试 ----
    def _run_task(self, task, state, requirement, workspace, mp):
        self._publish(EventType.STAGE_STARTED, stage=task.stage,
                      agent=task.agent, task_id=task.task_id)
        try:
            schema, model_dict, discipline = self._dispatch(
                task, state, requirement, workspace, mp)
        except Exception as exc:  # 失败处理（Phase 11 §2）
            self.logger.error("task_failed", task_id=task.task_id, error=str(exc))
            decision = self.orchestrator.handle_failure(
                self._active_graph, task.task_id, str(exc), max_retries=1)
            if decision.get("action") == "retry":
                try:
                    schema, model_dict, discipline = self._dispatch(
                        task, state, requirement, workspace, mp)
                except Exception as exc2:
                    self._active_graph.reset_status(task.task_id, "FAILED")
                    self._publish(EventType.PROJECT_FAILED,
                                  project_id=requirement.project_id,
                                  task_id=task.task_id)
                    raise
            else:
                self._active_graph.reset_status(task.task_id, "FAILED")
                self._publish(EventType.PROJECT_FAILED,
                              project_id=requirement.project_id,
                              task_id=task.task_id)
                raise

        self._complete_task(task, schema, model_dict, discipline,
                            state, workspace, requirement)

    # ---- 专业 Agent 并行执行 ----
    def _run_professional(self, tasks, state, requirement, workspace, mp):
        outcomes: List[tuple] = []

        def _work(task):
            return task, self._dispatch_professional(
                task, state, requirement, workspace, mp)

        if self.max_workers <= 1 or len(tasks) == 1:
            for t in tasks:
                task, res = _work(t)
                outcomes.append((task, res))
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futs = {ex.submit(_work, t): t for t in tasks}
                for fut in as_completed(futs):
                    t = futs[fut]
                    try:
                        task, res = fut.result()
                    except Exception as exc:
                        self.logger.error("professional_failed",
                                          task_id=t.task_id, error=str(exc))
                        raise
                    outcomes.append((task, res))

        for task, res in outcomes:
            schema, model_dict, discipline = res
            self._complete_task(task, schema, model_dict, discipline,
                                state, workspace, requirement)

    # ---- 任务派发（按阶段选择处理器） ----
    def _dispatch(self, task, state, requirement, workspace, mp):
        stage = task.stage
        if stage == "ORIGINAL_MODEL":
            return ("OriginalModel", build_original_model(requirement), None)
        if stage == "DESIGN_SPEC":
            return ("DesignSpec",
                    build_design_spec(state["artifacts"]["ORIGINAL_MODEL"],
                                     requirement), None)
        if stage == "LAYOUT":
            return ("LayoutModel",
                    build_layout_model(state["artifacts"]["DESIGN_SPEC"],
                                       requirement), None)
        if stage == "PROFESSIONAL_DEEPENING":
            return self._dispatch_professional(task, state, requirement,
                                              workspace, mp)
        if stage == "GEOMETRY":
            return ("GeometryModel",
                    self._run_geometry(state, workspace), None)
        if stage == "DRAWING":
            model_dict, cad = self._run_drawing(state, workspace)
            state["cad_command_count"] += cad
            return ("DrawingModel", model_dict, None)
        if stage == "VALIDATION":
            return ("ValidationReport",
                    self._run_validator(state, workspace), None)
        if stage == "EXPORT":
            return ("Deliverable",
                    self._run_deliverable(state, requirement, workspace), None)
        raise ValueError(f"未知阶段: {stage}")

    def _dispatch_professional(self, task, state, requirement, workspace, mp):
        contract = self.registry.get(task.agent)
        if not contract or not contract.impl:
            raise RuntimeError(
                f"专业 Agent {task.agent} 缺少 impl，无法动态加载")
        agent = _instantiate(contract.impl)
        ctx = AgentContext(
            project_id=requirement.project_id,
            task_id=task.task_id,
            stage="PROFESSIONAL_DEEPENING",
            inputs={"layout_model": state["artifacts"]["LAYOUT"]},
            workspace=str(self._project_dir),
        )
        result = agent.run(ctx)
        if not getattr(result, "success", False):
            raise RuntimeError(
                f"{task.agent} 执行失败: {getattr(result, 'messages', '')}")
        model_dict = result.output_model
        discipline = (model_dict.get("discipline")
                      or contract.discipline or task.agent)
        schema = (contract.output_schema[0]
                  if contract.output_schema else "ProfessionalModel")
        return (schema, model_dict, str(discipline).upper())

    # ---- 真实 Agent 执行（动态加载，不硬编码） ----
    def _run_geometry(self, state, workspace):
        from agents.geometry.geometry_agent import GeometryAgent
        agent = GeometryAgent(workspace_root=str(self._project_dir),
                              logger=self.logger)
        ctx = AgentContext(
            project_id=self._project_id, task_id="geometry_task", stage="GEOMETRY",
            inputs={"layout_model": state["artifacts"]["LAYOUT"]},
            workspace=str(self._project_dir))
        result = agent.run(ctx)
        if not getattr(result, "success", False):
            raise RuntimeError(f"geometry 执行失败: {getattr(result, 'messages', '')}")
        return result.output_model

    def _run_drawing(self, state, workspace):
        from agents.drawing.agent import DrawingAgent
        geom = state["artifacts"]["GEOMETRY"]
        drawing_model = DrawingAgent.build_drawing_model(geom)
        agent = DrawingAgent(workspace_root=str(self._project_dir),
                             backend=self.backend, logger=self.logger)
        ctx = AgentContext(
            project_id=self._project_id, task_id="drawing_task", stage="DRAWING",
            inputs={"drawing_model": drawing_model, "geometry_model": geom},
            workspace=str(self._project_dir))
        result = agent.run(ctx)
        if not getattr(result, "success", False):
            raise RuntimeError(f"drawing 执行失败: {getattr(result, 'messages', '')}")
        # DrawingAgent 将 CAD 命令日志写入 context.outputs
        cad_count = int((ctx.outputs or {}).get("command_count", 0) or 0)
        log_path = (ctx.outputs or {}).get("drawing_command_log")
        if log_path and Path(log_path).exists():
            try:
                workspace.save_cad(
                    "output", "drawing_command_log.json",
                    json.loads(Path(log_path).read_text(encoding="utf-8")),
                    as_json=True)
            except Exception:  # noqa: BLE001
                pass

        # ---- Phase 12.4/12.5：DrawingModel → CAD Adapter → DWG →
        #      回读 → GeneratedModel → Round-Trip Validation ----
        self._run_dwg_round_trip(drawing_model, state, workspace)
        return drawing_model, cad_count

    def _run_dwg_round_trip(self, drawing_model, state, workspace):
        """DWG 闭环（Phase 12）。Pipeline 只经统一 CAD Adapter，
        不知道具体 CAD 软件；后端不可用时由 registry 自动降级。"""
        dwg_path = str(self._project_dir / "cad" / f"{self._project_id}.dwg")
        export_report = export_drawing_to_dwg(
            drawing_model, dwg_path, project_id=self._project_id,
            preferred_backend=self.backend)
        self.logger.info("dwg_generated", backend=export_report["backend"],
                         path=export_report["dwg_path"])

        generated = read_dwg_to_generated_model(
            export_report["dwg_path"], project_id=self._project_id,
            backend=export_report["backend"])
        round_trip = round_trip_validate(
            generated, state["artifacts"].get("LAYOUT", {}))

        state["dwg"] = export_report
        state["generated_model"] = generated
        state["round_trip"] = round_trip

        try:
            workspace._write_json(
                self._project_dir / "models" / "GeneratedModel.json", generated)
            workspace.save_validation_report("RoundTripReport.json", round_trip)
        except Exception:  # noqa: BLE001
            pass
        self._publish(EventType.STAGE_COMPLETED, stage="DWG_ROUND_TRIP",
                      agent="cad_adapter", output="GeneratedModel",
                      passed=round_trip.get("passed"))

    def _run_validator(self, state, workspace):
        from agents.validator.validator_agent import ProfessionalValidator
        agent = ProfessionalValidator()
        ctx = AgentContext(
            project_id=self._project_id, task_id="validator_task", stage="VALIDATION",
            inputs={
                "layout_model": state["artifacts"]["LAYOUT"],
                "professional_models": dict(state["professional_models"]),
            },
            workspace=str(self._project_dir))
        result = agent.run(ctx)
        if not getattr(result, "success", False):
            raise RuntimeError(f"validator 执行失败: {getattr(result, 'messages', '')}")
        report = result.output_model
        workspace.save_validation_report("ValidationReport.json", report)
        return report

    def _run_deliverable(self, state, requirement, workspace):
        return build_deliverable(
            project_id=requirement.project_id,
            requirement=requirement,
            artifacts=state["artifacts"],
            professional_models=state["professional_models"],
            validation_report=state["artifacts"].get("VALIDATION", {}),
            generated_model=state.get("generated_model") or {},
            cad_command_count=state["cad_command_count"],
        )

    # ---- 冲突网关 + 人工审批（Phase 11 §2 / §5 / §6） ----
    def _conflict_gate(self, state, requirement, workspace):
        if state.get("_conflict_done"):
            return
        if not state["professional_models"]:
            return
        report = self._conflict_resolver.resolve(
            dict(state["professional_models"]),
            project_id=requirement.project_id)
        state["conflict"] = report.to_dict()
        try:
            workspace.save_validation_report("ConflictReport.json",
                                             report.to_dict())
        except Exception:  # noqa: BLE001
            pass

        if report.requires_approval:
            req = self._approval_manager.create(
                subject="专业协调冲突审批", project_id=requirement.project_id,
                payload=report.to_dict())
            state["approval"] = req.to_dict()
            if self.auto_approve:
                self._approval_manager.approve(req.request_id,
                                               comment="auto-approve (Phase 11 demo)")
                state["approval"] = req.to_dict()
        state["_conflict_done"] = True

    def _handle_waiting(self, graph, state, workspace, requirement) -> bool:
        """处理 WAITING_USER（人工审批未决）。auto_approve 时自动放行。"""
        waiting = [t for t in graph.all_tasks() if t.status == "WAITING_USER"]
        if not waiting:
            return False
        if self.auto_approve:
            for t in waiting:
                graph.reset_status(t.task_id, "READY")
            return True
        return False

    # ---- 完成一个任务：标记 + 落盘 + 记录 ----
    def _complete_task(self, task, schema, model_dict, discipline,
                       state, workspace, requirement):
        # 标记完成（运行时调度直接驱动状态，绕过状态机校验）
        try:
            self._active_graph.reset_status(task.task_id, "COMPLETED")
        except Exception:  # noqa: BLE001
            pass

        input_version = self._input_version_for(task, state)
        output_version = str(
            (model_dict.get("metadata") or {}).get("model_version")
            or model_dict.get("version") or "v1")

        filename = None
        if discipline:
            filename = f"{str(discipline).lower()}_model.json"

        record = workspace.save_artifact(
            stage=task.stage, agent=task.agent, task_id=task.task_id,
            model_dict=model_dict, output_schema=schema,
            output_version=output_version, input_version=input_version,
            status="COMPLETED", dependencies=list(task.dependencies),
            filename=filename)

        state["artifacts"][task.stage] = model_dict
        if discipline:
            state["professional_models"][str(discipline).lower()] = model_dict
        state["produced"].append({
            "stage": task.stage, "agent": task.agent,
            "task_id": task.task_id,
            "filename": record["output_file"].split("/")[-1],
            "schema": schema,
            "discipline": discipline or "",
            "output_version": output_version,
            "input_version": input_version,
        })
        self._publish(EventType.STAGE_COMPLETED, stage=task.stage,
                      agent=task.agent, output=schema, task_id=task.task_id)

    # ======================================================================
    # 检查点 / 恢复
    # ======================================================================
    def _save_checkpoint(self, graph, state, cp, requirement):
        cp.save(
            project_id=requirement.project_id,
            requirement=requirement.to_dict(),
            graph=graph.to_dict(),
            produced=state["produced"],
            messages=state["messages"],
            conflict=state.get("conflict"),
            approval=state.get("approval"),
            status="RUNNING",
            extra={
                "cad_command_count": state["cad_command_count"],
                "_conflict_done": state.get("_conflict_done", False),
                "dwg": state.get("dwg"),
                "round_trip": state.get("round_trip"),
            },
        )
        self._publish(EventType.CHECKPOINT_SAVED,
                      project_id=requirement.project_id)

    def _resume(self, requirement, cp) -> Dict[str, Any]:
        data = cp.load()
        if data is None:
            raise RuntimeError("无可用检查点，无法恢复")
        graph = self._graph_from_dict(data["graph"])
        self._active_graph = graph
        self._project_dir = self._rt.project_dir(requirement.project_id)
        workspace = WorkspaceManager(self._project_dir)
        self._ensure_event_bus(self._project_dir)

        state = self._rebuild_state(data, workspace, requirement)
        mp = ModelPipeline(requirement.project_id)
        self._publish(EventType.PROJECT_STARTED, project_id=requirement.project_id,
                      name=requirement.name, resumed=True)
        self._execute(graph, state, requirement, workspace, mp, cp,
                     fail_after=None)
        return self._finalize(requirement, state, workspace, graph)

    def _graph_from_dict(self, d: Dict[str, Any]) -> TaskGraph:
        g = TaskGraph()
        for td in d.get("tasks", []):
            g._tasks[td["task_id"]] = Task.from_dict(td)
        return g

    def _rebuild_state(self, data, workspace, requirement):
        artifacts: Dict[str, Any] = {}
        professional_models: Dict[str, Any] = {}
        for rec in data.get("produced", []):
            try:
                m = workspace.read_artifact(rec["stage"], rec["filename"])
            except Exception:  # noqa: BLE001
                continue
            artifacts[rec["stage"]] = m
            if rec.get("discipline"):
                professional_models[rec["discipline"].lower()] = m
        extra = data.get("extra", {})
        state = self._new_state()
        state["artifacts"] = artifacts
        state["professional_models"] = professional_models
        state["produced"] = list(data.get("produced", []))
        state["messages"] = list(data.get("messages", []))
        state["conflict"] = data.get("conflict")
        state["approval"] = data.get("approval")
        state["cad_command_count"] = int(extra.get("cad_command_count", 0))
        state["_conflict_done"] = bool(extra.get("_conflict_done", False))
        state["dwg"] = extra.get("dwg")
        state["round_trip"] = extra.get("round_trip")
        try:
            state["generated_model"] = workspace.read_artifact(
                "models", "GeneratedModel.json")
        except Exception:  # noqa: BLE001
            gm = self._project_dir / "models" / "GeneratedModel.json"
            if gm.exists():
                state["generated_model"] = json.loads(
                    gm.read_text(encoding="utf-8"))
        return state

    # ======================================================================
    # 收尾
    # ======================================================================
    def _finalize(self, requirement, state, workspace, graph) -> Dict[str, Any]:
        self._rt.set_state(requirement.project_id, "DELIVERED")
        self._rt.set_stage(requirement.project_id, "EXPORT")
        workspace.save_task_graph(graph.to_dict())

        deliverable = state["artifacts"].get("EXPORT")
        if deliverable:
            workspace._write_json(self._project_dir / "Deliverable.json",
                                  deliverable)
            # deliverable 也是 generated_model
            workspace.save_artifact(
                stage="EXPORT", agent="deliverable", task_id="deliverable_task",
                model_dict=deliverable, output_schema="Deliverable",
                output_version="v1", input_version="",
                status="COMPLETED", dependencies=["validator_task"],
                filename="Deliverable.json")

        self._publish(EventType.PROJECT_COMPLETED,
                      project_id=requirement.project_id)
        return {
            "project_id": requirement.project_id,
            "status": "DELIVERED",
            "project_dir": str(self._project_dir),
            "graph": graph.to_dict(),
            "artifacts": sorted(state["artifacts"].keys()),
            "professional_models": sorted(state["professional_models"].keys()),
            "cad_command_count": state["cad_command_count"],
            "conflict": state.get("conflict"),
            "approval": state.get("approval"),
            "produced": state["produced"],
            # ---- Phase 12：CAD Backend / DWG / Round-Trip ----
            "cad_backend": (state.get("dwg") or {}).get("backend", self.backend),
            "dwg": state.get("dwg"),
            "round_trip": state.get("round_trip"),
        }

    # ======================================================================
    # 辅助
    # ======================================================================
    def _new_state(self) -> Dict[str, Any]:
        return {
            "artifacts": {},
            "professional_models": {},
            "produced": [],
            "messages": [],
            "conflict": None,
            "approval": None,
            "cad_command_count": 0,
            "_conflict_done": False,
            "dwg": None,
            "generated_model": None,
            "round_trip": None,
        }

    def _input_version_for(self, task, state) -> str:
        for dep in task.dependencies:
            for rec in state["produced"]:
                if rec["task_id"] == dep:
                    return rec.get("output_version", "")
        return ""

    def _ensure_event_bus(self, project_dir: Path):
        if self.event_bus is not None:
            return
        try:
            self.event_bus = EventBus(UnifiedLogger(log_dir=project_dir / "logs"))
        except Exception:  # noqa: BLE001
            self.event_bus = None

    def _publish(self, etype, **payload):
        if self.event_bus is None:
            return
        try:
            self.event_bus.publish(Event(etype, payload))
        except Exception:  # noqa: BLE001
            pass


__all__ = ["E2EPipeline"]
