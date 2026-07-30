"""runtime.pipeline.pipeline_runner · 端到端设计流水线编排（Phase 8 §1）。

职责（仅编排，不含业务逻辑）：
  - 创建 Project
  - 初始化 Context
  - 创建 TaskGraph
  - 调度 Agent（geometry / drawing）
  - 保存 checkpoint

业务转换逻辑位于各 Agent：
  - GeometryAgent：LayoutModel -> GeometryModel（坐标 / 墙线 / 家具定位转换）
  - DrawingAgent  ：GeometryModel -> DrawingModel（图层 / 实体 / 尺寸）+ CAD Mock 执行

禁止：直接生成 DWG / 调用 AutoCAD / AI 自动布局 / 装修算法优化。
"""
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.context import AgentContext
from core.logging import build_logger
from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.task_graph import TaskGraph
from agents.geometry.geometry_agent import GeometryAgent
from agents.drawing.agent import DrawingAgent
from models.model_pipeline import ModelPipeline
from models.geometry import GeometryModel
from models.drawing import DrawingModel
from models.generated import GeneratedModel
from runtime.pipeline.professional_pipeline import ProfessionalPipeline
from runtime.pipeline.orchestrated_pipeline import OrchestratedPipeline
from runtime.pipeline.e2e_pipeline import E2EPipeline
from runtime.orchestrator.task_planner import ProjectRequirement


class PipelineRunner:
    """端到端设计流水线编排器。

    输入：一个 LayoutModel（dict）
    执行：pipeline.run(layout_model)
    得到：DrawingModel（JSON）+ drawing_command_log.json（CAD Mock 输出）
    全程无需人工干预（验收标准 §8）。

    专业深化（Phase 9 §4）：run(professional=True) 或 run_professional()
    在 layout -> geometry -> drawing 之间插入 PROFESSIONAL_DEEPENING 阶段，
    并行调度电气 / 照明 / 给排水 / 吊顶 / 施工 / 立面 Agent，并用 Validator 校验。
    """

    def __init__(self, workspace_root=None,
                 config: Optional[Dict[str, Any]] = None,
                 backend: Optional[str] = None, logger=None):
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.config = config or {}
        self.backend = backend or self.config.get("cad", {}).get("backend", "mock")
        self.logger = logger or build_logger()
        self.task_graph = None

    def run(self, layout_model: Dict[str, Any],
            project_id: Optional[str] = None,
            name: str = "design-pipeline",
            professional: bool = False) -> Dict[str, Any]:
        if professional:
            return self.run_professional(layout_model, project_id=project_id,
                                         name=name)
        project_id = project_id or f"proj-{uuid.uuid4().hex[:8]}"
        project_id = project_id or f"proj-{uuid.uuid4().hex[:8]}"
        rt = ProjectRuntime(workspace_root=self.workspace_root)
        project = rt.create(project_id, name=name)
        project_dir = rt.project_dir(project_id)
        self.logger.info(f"[pipeline] 创建工程 {project_id} @ {project_dir}")

        # ---- 版本链（§2 / §7）----
        mp = ModelPipeline(project_id)
        mp.observe("layout", layout_model)

        # ---- TaskGraph（§1）----
        tg = TaskGraph()
        tg.create_task("geometry", agent="geometry", stage="GEOMETRY",
                       dependencies=[], status="READY")
        tg.create_task("drawing", agent="drawing", stage="DRAWING",
                       dependencies=["geometry"], status="READY")

        messages: List[str] = []
        try:
            # ---- LayoutModel 落盘 ----
            self._save(project_dir / "LayoutModel.json", layout_model)

            # ---- Geometry Agent（Layout → Geometry）----
            geo_agent = GeometryAgent(workspace_root=project_dir, logger=self.logger)
            geo_ctx = self._context(project_id, "geometry", project_dir,
                                    {"layout_model": layout_model})
            geo_result = geo_agent.run(geo_ctx)
            if not geo_result.success:
                raise RuntimeError("; ".join(geo_result.messages))
            geometry = mp.attach("geometry", "geometry", geo_ctx.task_id,
                                 geo_result.output_model, parent=layout_model)
            self._save(project_dir / "GeometryModel.json", geometry)
            GeometryModel.from_dict(geometry)  # 结构完整性校验
            tg.reset_status("geometry", "COMPLETED")
            messages.append(f"Geometry: {len(geometry.get('rooms', []))} 房间 / "
                            f"{len(geometry.get('walls', []))} 墙线")

            # ---- Drawing Agent（Geometry → Drawing + CAD Mock 执行）----
            drawing_payload = DrawingAgent.build_drawing_model(geometry)
            drawing = mp.attach("drawing", "drawing", f"drawing-{project_id}",
                                drawing_payload, parent=geometry)
            self._save(project_dir / "DrawingModel.json", drawing)
            DrawingModel.from_dict(drawing)  # 结构完整性校验

            draw_agent = DrawingAgent(workspace_root=project_dir,
                                      backend=self.backend,
                                      cad_config=self.config, logger=self.logger)
            draw_ctx = self._context(project_id, "drawing", project_dir,
                                     {"drawing_model": drawing,
                                      "geometry_model": geometry})
            draw_result = draw_agent.run(draw_ctx)
            if not draw_result.success:
                raise RuntimeError("; ".join(draw_result.messages))
            command_count = draw_ctx.outputs.get("command_count", 0)
            messages.append(f"Drawing: {command_count} CAD commands")
            tg.reset_status("drawing", "COMPLETED")

            # ---- GeneratedModel（CAD 执行结果摘要）----
            generated_payload = {
                "source_project_id": project_id,
                "drawing_model_ref": "DrawingModel.json",
                "cad_backend": self.backend,
                "command_count": command_count,
                "drawing_command_log": "drawing_command_log.json",
                "summary": {"status": "MOCK_EXECUTED", "messages": messages},
            }
            generated = mp.attach("generated", "pipeline",
                                  f"generated-{project_id}",
                                  generated_payload, parent=drawing)
            self._save(project_dir / "GeneratedModel.json", generated)
            GeneratedModel.from_dict(generated)  # 结构完整性校验

            # ---- Checkpoint / 工程文件（§1）----
            self._save(project_dir / "model_chain.json", mp.to_dict())
            self._save(project_dir / "task_graph.json", tg.to_dict())
            self._save(project_dir / "project.json",
                       {**project,
                        "pipeline": {"status": "COMPLETED",
                                     "backend": self.backend,
                                     "model_chain": mp.to_dict()}})

            return {
                "project_id": project_id,
                "status": "COMPLETED",
                "project_dir": str(project_dir),
                "models": {
                    "layout": str(project_dir / "LayoutModel.json"),
                    "geometry": str(project_dir / "GeometryModel.json"),
                    "drawing": str(project_dir / "DrawingModel.json"),
                    "generated": str(project_dir / "GeneratedModel.json"),
                },
                "drawing_command_log": str(project_dir / "drawing_command_log.json"),
                "model_chain": str(project_dir / "model_chain.json"),
                "command_count": command_count,
                "backend": self.backend,
                "messages": messages,
            }
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"[pipeline] 执行失败：{e}")
            self._save(project_dir / "model_chain.json", mp.to_dict())
            self._save(project_dir / "task_graph.json", tg.to_dict())
            return {
                "project_id": project_id,
                "status": "FAILED",
                "project_dir": str(project_dir),
                "error": str(e),
                "messages": messages,
            }

    def run_professional(self, layout_model: Dict[str, Any],
                         project_id: Optional[str] = None,
                         name: str = "professional-pipeline",
                         max_workers: int = 4) -> Dict[str, Any]:
        """专业深化流水线入口（Phase 9 §4）：插入 PROFESSIONAL_DEEPENING 阶段。"""
        pp = ProfessionalPipeline(
            workspace_root=self.workspace_root, config=self.config,
            backend=self.backend, logger=self.logger, max_workers=max_workers)
        result = pp.run(layout_model, project_id=project_id, name=name)
        self.task_graph = pp.task_graph
        return result

    def run_orchestrated(self, requirement, layout_model=None,
                         project_id: Optional[str] = None,
                         name: str = "orchestrated-pipeline",
                         max_workers: int = 4,
                         auto_approve: bool = True) -> Dict[str, Any]:
        """动态编排入口（Phase 10 §7）：Orchestrator -> TaskGraph -> Agent 执行。

        requirement 可为 ProjectRequirement 或 dict；若提供 layout_model，
        则并入 requirement.inputs（layout 任务直通已有 LayoutModel）。
        """
        if isinstance(requirement, dict):
            requirement = ProjectRequirement.from_dict(requirement)
        if project_id:
            requirement.project_id = project_id
        if name:
            requirement.name = name
        if layout_model is not None:
            requirement.inputs.setdefault("layout_model", layout_model)

        op = OrchestratedPipeline(
            workspace_root=self.workspace_root, config=self.config,
            backend=self.backend, logger=self.logger,
            max_workers=max_workers, auto_approve=auto_approve)
        result = op.run(requirement)
        self.task_graph = op.task_graph
        return result

    def run_e2e(self, requirement, resume: bool = False,
                max_workers: int = 4, auto_approve: bool = True,
                event_bus=None, fail_after: Optional[str] = None) -> Dict[str, Any]:
        """完整运行时集成入口（Phase 11 §1/§5/§7）。

        从用户需求（含结构化 rooms/area 等）出发，经 Orchestrator 生成完整
        TaskGraph 并驱动 Runtime Pipeline 完成：
            parser -> design -> layout -> 专业(并行) -> geometry
            -> drawing(CAD Mock) -> validator -> deliverable
        支持 resume 从中断处续跑；fail_after 用于测试模拟中断。
        """
        if isinstance(requirement, dict):
            requirement = ProjectRequirement.from_dict(requirement)
        ep = E2EPipeline(
            workspace_root=self.workspace_root, backend=self.backend,
            logger=self.logger, max_workers=max_workers,
            auto_approve=auto_approve, event_bus=event_bus)
        result = ep.run(requirement, resume=resume, fail_after=fail_after)
        self.task_graph = ep._active_graph
        return result

    def _context(self, project_id, agent, project_dir, inputs):
        return AgentContext(
            project_id=project_id,
            task_id=f"{agent}-{project_id}",
            stage=agent.upper(),
            inputs=inputs,
            workspace=str(project_dir),
        )

    def _save(self, path, data: Dict[str, Any]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
