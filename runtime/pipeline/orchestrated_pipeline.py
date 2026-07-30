"""runtime.pipeline.orchestrated_pipeline · 动态编排流水线（Phase 10 §7）。

由“固定 Pipeline”升级为“Orchestrator → TaskGraph → Agent 执行”的动态编排：

    ProjectRequirement
        → OrchestratorAgent / TaskPlanner 动态生成 TaskGraph（不写死顺序）
        → 按依赖关系逐轮调度 Agent（专业 Agent 并行）
        → 专业深化后进行冲突检测（ConflictResolver）+ Human Approval 网关
        → 继续 Geometry / Drawing / Validation
        → 保存 Checkpoint，支持失败恢复

禁止：AutoCAD 开发 / DWG 解析 / AI 设计算法 / 施工规范知识库 / 修改 CAD 抽象层。
Agent 的类由 agent_contract.json 的 impl 字段动态解析（禁止在流水线里硬编码 Agent 顺序）。
"""
from __future__ import annotations

import importlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.context import AgentContext
from core.logging import build_logger
from runtime.project_runtime import ProjectRuntime
from models.model_pipeline import ModelPipeline

from runtime.agent_registry.registry import AgentCapabilityRegistry, AgentContract
from runtime.orchestrator.task_planner import ProjectRequirement, TaskPlanner
from runtime.router.schema_router import SchemaRouter
from runtime.conflict.resolver import ConflictResolver
from runtime.approval.approval import ApprovalManager, ApprovalStatus
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
from agents.orchestrator.task_graph import TaskGraph
from agents.drawing.agent import DrawingAgent

_PROFESSIONAL_CAP = "professional_deepening"


class OrchestratedPipeline:
    """智能编排流水线：输入项目需求，自动完成建项 → 规划 → 调度 → 校验。"""

    def __init__(self, workspace_root=None, config=None, backend=None,
                 logger=None, max_workers: int = 4, auto_approve: bool = True):
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.config = config or {}
        self.backend = backend or self.config.get("cad", {}).get("backend", "mock")
        self.logger = logger or build_logger()
        self.max_workers = max_workers
        self.auto_approve = auto_approve
        self.registry = AgentCapabilityRegistry()
        self.planner = TaskPlanner(registry=self.registry)
        self.router = SchemaRouter(registry=self.registry)
        self.orchestrator = OrchestratorAgent(registry=self.registry)
        self.approval_manager = ApprovalManager()
        self.task_graph: Optional[TaskGraph] = None

    # ================================================================= #
    def run(self, requirement: ProjectRequirement) -> Dict[str, Any]:
        project_id = requirement.project_id or f"proj-{uuid.uuid4().hex[:8]}"
        requirement.project_id = project_id
        rt = ProjectRuntime(workspace_root=self.workspace_root)
        project = rt.create(project_id, name=requirement.name)
        project_dir = rt.project_dir(project_id)
        self.logger.info(f"[orchestrated] 创建工程 {project_id} @ {project_dir}")

        # ---- 1) 分析需求 + 动态生成 TaskGraph（Orchestrator）----
        tg = self.orchestrator.create_task_graph(requirement)
        self.task_graph = tg
        plan = [t.task_id for t in tg.all_tasks()]
        self._save(project_dir / "orchestration_plan.json", {
            "requirement": requirement.to_dict(),
            "analysis": self.orchestrator.analyze_goal(requirement),
            "task_graph": tg.to_dict(),
            "data_flow": [e.to_dict()
                          for e in self.router.build_flow(requirement.initial_schemas)],
        })
        self.logger.info(f"[orchestrated] 生成任务：{plan}")

        mp = ModelPipeline(project_id)
        artifacts: Dict[str, Any] = {}       # schema -> model dict
        professional_models: Dict[str, Any] = {}
        messages: List[str] = []
        command_count = 0
        conflict_report = None
        gate_done = False
        status = "COMPLETED"

        # ---- layout 直通：需求携带的 LayoutModel 作为初始数据 ----
        layout_model = requirement.inputs.get("layout_model")

        try:
            round_no = 0
            while not tg.is_complete():
                runnable = tg.get_runnable()
                if not runnable:
                    break
                round_no += 1
                prof_tasks = [t for t in runnable
                              if _PROFESSIONAL_CAP in t.parameters.get("capabilities", [])]
                other_tasks = [t for t in runnable if t not in prof_tasks]

                # 专业 Agent 并行执行（§3 验收：专业 Agent 可并行）
                if prof_tasks:
                    raw = self._run_parallel(prof_tasks, project_id, project_dir,
                                             artifacts, layout_model)
                    for task, out_schema, out_model in raw:
                        stamped = mp.attach(task.agent, task.agent, task.task_id,
                                            out_model, parent=layout_model)
                        artifacts[out_schema] = stamped
                        disc = task.parameters.get("discipline") or task.agent
                        professional_models[disc] = stamped
                        self._save(project_dir / f"{out_schema}.json", stamped)
                        tg.update_status(task.task_id, "RUNNING")
                        tg.update_status(task.task_id, "VALIDATING")
                        tg.update_status(task.task_id, "COMPLETED")
                        messages.append(
                            f"{task.agent}: {stamped['version']['model_version']}")

                # 其它 Agent（layout/geometry/drawing/validator）串行执行
                for task in other_tasks:
                    self._execute_serial(task, tg, mp, artifacts,
                                         professional_models, project_id,
                                         project_dir, layout_model, messages)
                    if task.parameters.get("_command_count"):
                        command_count = task.parameters["_command_count"]

                # 冲突检测 + Human Approval 网关（专业深化全部完成后触发一次）
                if not gate_done and self._professional_done(tg) and professional_models:
                    conflict_report, req = self._conflict_gate(
                        professional_models, project_id, project_dir, messages)
                    gate_done = True
                    if req is not None and req.status != ApprovalStatus.APPROVED.value:
                        # 未批准：下游任务进入 WAITING_USER，流水线暂停等待人工
                        status = "WAITING_USER"
                        for t in tg.all_tasks():
                            if t.status in ("READY", "PENDING"):
                                tg.reset_status(t.task_id, "WAITING_USER")
                        break

                # Checkpoint（每轮保存，支持失败恢复）
                self._save_checkpoint(project_dir, tg, mp)

            if tg.has_failed():
                status = "FAILED"

            # ---- GeneratedModel（CAD Mock 执行摘要）----
            if "DrawingModel" in artifacts:
                generated_payload = {
                    "source_project_id": project_id,
                    "cad_backend": self.backend,
                    "command_count": command_count,
                    "professional_models": list(professional_models.keys()),
                    "validation_status": (artifacts.get("ValidationReport") or {}).get("status"),
                    "summary": {"status": "MOCK_EXECUTED", "messages": messages},
                }
                generated = mp.attach("generated", "pipeline",
                                      f"generated-{project_id}", generated_payload,
                                      parent=artifacts.get("DrawingModel"))
                artifacts["GeneratedModel"] = generated
                self._save(project_dir / "GeneratedModel.json", generated)

            self._save_checkpoint(project_dir, tg, mp)
            self._save(project_dir / "project.json", {
                **project,
                "pipeline": {"status": status, "backend": self.backend,
                             "mode": "orchestrated",
                             "model_chain": mp.to_dict()},
            })

            return {
                "project_id": project_id,
                "status": status,
                "project_dir": str(project_dir),
                "plan": plan,
                "tasks": {t.task_id: t.status for t in tg.all_tasks()},
                "professional_models": list(professional_models.keys()),
                "artifacts": {s: str(project_dir / f"{s}.json")
                              for s in artifacts},
                "conflict_report": conflict_report.to_dict() if conflict_report else None,
                "command_count": command_count,
                "backend": self.backend,
                "validation_status": (artifacts.get("ValidationReport") or {}).get("status"),
                "messages": messages,
            }
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"[orchestrated] 执行失败：{e}")
            self._save_checkpoint(project_dir, tg, mp)
            return {
                "project_id": project_id,
                "status": "FAILED",
                "project_dir": str(project_dir),
                "error": str(e),
                "messages": messages,
            }

    # ================================================================= #
    # 执行：专业 Agent 并行（纯计算），返回后串行打标
    def _run_parallel(self, tasks, project_id, project_dir, artifacts,
                      layout_model) -> List[Tuple[Any, str, Dict[str, Any]]]:
        def _one(task):
            contract = self.registry.get(task.agent)
            agent = self._instantiate(contract, project_dir)
            ctx = AgentContext(
                project_id=project_id, task_id=task.task_id,
                stage="PROFESSIONAL_DEEPENING",
                inputs={"layout_model": layout_model},
                workspace=str(project_dir))
            res = agent.run(ctx)
            if not res.success:
                raise RuntimeError(f"{task.agent}: " + "; ".join(res.messages))
            out_schema = (contract.output_schema or [task.agent])[0]
            return task, out_schema, res.output_model

        out: List[Tuple[Any, str, Dict[str, Any]]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = [ex.submit(_one, t) for t in tasks]
            for fut in futures:
                out.append(fut.result())
        return out

    # 执行：layout / geometry / drawing / validator（串行）
    def _execute_serial(self, task, tg: TaskGraph, mp: ModelPipeline,
                        artifacts: Dict[str, Any],
                        professional_models: Dict[str, Any],
                        project_id: str, project_dir: Path,
                        layout_model, messages: List[str]) -> None:
        contract = self.registry.get(task.agent)
        caps = set(task.parameters.get("capabilities", [])
                   or (contract.capabilities if contract else []))
        out_schema = (task.parameters.get("output_schema")
                      or (contract.output_schema if contract else []) or [task.agent])[0]

        try:
            tg.update_status(task.task_id, "RUNNING")

            # ---- layout：直通（不生成模型，只提供已有 LayoutModel）----
            if task.agent == "layout" or (contract and not contract.impl
                                          and "LayoutModel" in (contract.output_schema or [])):
                if layout_model is None:
                    raise RuntimeError("需求缺少 inputs.layout_model")
                stamped = mp.observe("layout", layout_model)
                artifacts["LayoutModel"] = layout_model
                self._save(project_dir / "LayoutModel.json", layout_model)
                messages.append(f"layout: {len(layout_model.get('rooms', []))} 房间")
                tg.update_status(task.task_id, "VALIDATING")
                tg.update_status(task.task_id, "COMPLETED")
                return

            # ---- drawing：Geometry -> Drawing + CAD Mock ----
            if "drawing_generate" in caps:
                geometry = artifacts["GeometryModel"]
                drawing_payload = DrawingAgent.build_drawing_model(geometry)
                drawing = mp.attach("drawing", "drawing", task.task_id,
                                    drawing_payload, parent=geometry)
                artifacts["DrawingModel"] = drawing
                self._save(project_dir / "DrawingModel.json", drawing)
                agent = self._instantiate(contract, project_dir)
                ctx = self._ctx(project_id, task.task_id, "DRAWING", project_dir,
                                {"drawing_model": drawing, "geometry_model": geometry})
                res = agent.run(ctx)
                if not res.success:
                    raise RuntimeError("; ".join(res.messages))
                task.parameters["_command_count"] = ctx.outputs.get("command_count", 0)
                messages.append(f"drawing: {task.parameters['_command_count']} CAD commands")
                tg.update_status(task.task_id, "VALIDATING")
                tg.update_status(task.task_id, "COMPLETED")
                return

            # ---- geometry / validator：通用 impl 执行 ----
            agent = self._instantiate(contract, project_dir)
            ctx = self._ctx(project_id, task.task_id,
                            self._stage_of(caps), project_dir,
                            self._build_inputs(caps, artifacts, professional_models,
                                               layout_model))
            res = agent.run(ctx)
            if not res.success:
                raise RuntimeError("; ".join(res.messages))
            stamped = mp.attach(task.agent, task.agent, task.task_id,
                                res.output_model, parent=layout_model)
            artifacts[out_schema] = stamped
            self._save(project_dir / f"{out_schema}.json", stamped)
            messages.append(f"{task.agent}: {out_schema}")
            tg.update_status(task.task_id, "VALIDATING")
            tg.update_status(task.task_id, "COMPLETED")
        except Exception as e:  # noqa: BLE001
            # 失败处理 + 触发恢复（一次重试）
            decision = self.orchestrator.handle_failure(tg, task.task_id, str(e))
            messages.append(f"{task.agent} 失败：{e} -> {decision['action']}")
            if decision["action"] == "retry":
                self.orchestrator.trigger_recovery(tg, task.task_id)
            else:
                raise

    # ================================================================= #
    def _conflict_gate(self, professional_models, project_id, project_dir,
                       messages):
        resolver = ConflictResolver()
        report = resolver.resolve(professional_models, project_id=project_id)
        self._save(project_dir / "ConflictReport.json", report.to_dict())
        if not report.requires_approval:
            messages.append("conflict: 无阻断性冲突")
            return report, None
        req = self.approval_manager.create(
            subject="专业冲突需人工确认", project_id=project_id,
            payload={"conflict_report": report.to_dict()})
        if self.auto_approve:
            self.approval_manager.approve(req.request_id, comment="非交互模式自动批准")
        self._save(project_dir / "approvals.json",
                   [r.to_dict() for r in self.approval_manager.all()])
        messages.append(
            f"conflict: {report.summary['conflict_count']} 冲突, approval={req.status}")
        return report, req

    # ---- 辅助 ----
    def _instantiate(self, contract: AgentContract, project_dir: Path):
        if contract is None or not contract.impl:
            raise RuntimeError(f"契约缺少 impl，无法实例化：{getattr(contract,'agent_name','?')}")
        module_name, class_name = contract.impl.split(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        caps = set(contract.capabilities)
        if "geometry_generate" in caps:
            return cls(workspace_root=project_dir, logger=self.logger)
        if "drawing_generate" in caps:
            return cls(workspace_root=project_dir, backend=self.backend,
                       cad_config=self.config, logger=self.logger)
        return cls()

    def _build_inputs(self, caps, artifacts, professional_models, layout_model):
        if "validate" in caps:
            return {"layout_model": artifacts.get("LayoutModel", layout_model),
                    "professional_models": professional_models}
        if "geometry_generate" in caps:
            return {"layout_model": artifacts.get("LayoutModel", layout_model)}
        return {"layout_model": artifacts.get("LayoutModel", layout_model)}

    @staticmethod
    def _stage_of(caps) -> str:
        if "validate" in caps:
            return "VALIDATION"
        if "geometry_generate" in caps:
            return "GEOMETRY"
        if "drawing_generate" in caps:
            return "DRAWING"
        return "PROFESSIONAL_DEEPENING"

    @staticmethod
    def _professional_done(tg: TaskGraph) -> bool:
        prof = [t for t in tg.all_tasks()
                if _PROFESSIONAL_CAP in t.parameters.get("capabilities", [])]
        if not prof:
            return False
        return all(t.status == "COMPLETED" for t in prof)

    def _ctx(self, project_id, task_id, stage, project_dir, inputs):
        return AgentContext(project_id=project_id, task_id=task_id, stage=stage,
                            inputs=inputs, workspace=str(project_dir))

    def _save_checkpoint(self, project_dir, tg: TaskGraph, mp: ModelPipeline):
        self._save(project_dir / "task_graph.json", tg.to_dict())
        self._save(project_dir / "model_chain.json", mp.to_dict())

    def _save(self, path, data) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")


__all__ = ["OrchestratedPipeline"]
