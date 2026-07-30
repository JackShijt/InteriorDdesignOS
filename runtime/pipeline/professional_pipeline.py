"""runtime.pipeline.professional_pipeline · 专业深化流水线（Phase 9 §3 / §4）。

职责（仅编排，不含业务逻辑）：
  - 创建 Project
  - 初始化 Context / TaskGraph（含 PROFESSIONAL_DEEPENING 阶段）
  - 并行调度专业 Agent（Electrical / Lighting / Plumbing / Ceiling 等）
  - 调度 Geometry / Drawing（复用既有 Agent，不破坏 CAD 抽象层）
  - 调度 ProfessionalValidator 产出 ValidationReport
  - 保存 checkpoint

版本传递由 ModelPipeline 负责（metadata / version / 版本链）。
禁止：直接生成 DWG / 调用 AutoCAD / AI 自动布局 / 装修算法优化。
"""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.context import AgentContext
from core.logging import build_logger
from runtime.project_runtime import ProjectRuntime
from agents.orchestrator.task_graph import TaskGraph
from models.model_pipeline import ModelPipeline
from models.geometry import GeometryModel
from models.drawing import DrawingModel
from models.generated import GeneratedModel

from agents.geometry.geometry_agent import GeometryAgent
from agents.drawing.agent import DrawingAgent
from agents.validator.validator_agent import ProfessionalValidator
from agents.electrical.electrical_agent import ElectricalAgent
from agents.lighting.lighting_agent import LightingAgent
from agents.plumbing.plumbing_agent import PlumbingAgent
from agents.ceiling.ceiling_agent import CeilingAgent
from agents.construction.construction_agent import ConstructionAgent
from agents.elevation.elevation_agent import ElevationAgent


# 专业 Agent 注册表：name -> (Agent 类, 输出文件名)
AGENT_REGISTRY = {
    "electrical": (ElectricalAgent, "ElectricalModel.json"),
    "lighting": (LightingAgent, "LightingModel.json"),
    "plumbing": (PlumbingAgent, "PlumbingModel.json"),
    "ceiling": (CeilingAgent, "CeilingModel.json"),
    "construction": (ConstructionAgent, "ConstructionModel.json"),
    "elevation": (ElevationAgent, "ElevationModel.json"),
}

# §3 明确并行组（其余专业 Agent 同样以并行方式执行）
PARALLEL_AGENTS = ["electrical", "lighting", "plumbing", "ceiling"]


class ProfessionalPipeline:
    """专业深化流水线编排器。

    输入：一个 LayoutModel（dict）
    执行：professional_pipeline.run(layout_model)
    得到：professional 模型（JSON）+ ValidationReport（JSON）+ DrawingModel + CAD Mock 输出
    全程无需人工干预。
    """

    def __init__(self, workspace_root=None, config=None,
                 backend=None, logger=None, max_workers: int = 4):
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.config = config or {}
        self.backend = backend or self.config.get("cad", {}).get("backend", "mock")
        self.logger = logger or build_logger()
        self.max_workers = max_workers
        self.task_graph: Optional[TaskGraph] = None

    def run(self, layout_model: Dict[str, Any],
            project_id: Optional[str] = None,
            name: str = "professional-pipeline") -> Dict[str, Any]:
        project_id = project_id or f"proj-{uuid.uuid4().hex[:8]}"
        rt = ProjectRuntime(workspace_root=self.workspace_root)
        project = rt.create(project_id, name=name)
        project_dir = rt.project_dir(project_id)
        self.logger.info(f"[professional] 创建工程 {project_id} @ {project_dir}")

        mp = ModelPipeline(project_id)
        mp.observe("layout", layout_model)

        # ---- TaskGraph（§4）：layout -> professional -> geometry -> drawing -> validation
        tg = TaskGraph()
        tg.create_task("layout", agent="layout", stage="LAYOUT",
                       dependencies=[], status="READY")
        tg.create_task("professional", agent="professional",
                       stage="PROFESSIONAL_DEEPENING",
                       dependencies=["layout"], status="READY")
        tg.create_task("geometry", agent="geometry", stage="GEOMETRY",
                       dependencies=["professional"], status="READY")
        tg.create_task("drawing", agent="drawing", stage="DRAWING",
                       dependencies=["geometry"], status="READY")
        tg.create_task("validation", agent="validator", stage="VALIDATION",
                       dependencies=["professional", "geometry", "drawing"],
                       status="READY")
        self.task_graph = tg

        messages: List[str] = []
        professional_models: Dict[str, Any] = {}
        try:
            # ---- LayoutModel 落盘 ----
            self._save(project_dir / "LayoutModel.json", layout_model)

            # ---- 专业 Agent 并行执行（§3）----
            raw = self._run_professional(layout_model, project_id, project_dir)
            for agent_name, out in raw.items():
                stamped = mp.attach(agent_name, agent_name,
                                    f"{agent_name}-{project_id}", out,
                                    parent=layout_model)
                professional_models[agent_name] = stamped
                _, fname = AGENT_REGISTRY[agent_name]
                self._save(project_dir / fname, stamped)
                messages.append(f"{agent_name}: "
                                f"{stamped['version']['model_version']}")
            tg.reset_status("professional", "COMPLETED")

            # ---- Geometry Agent（Layout -> Geometry）----
            geo_agent = GeometryAgent(workspace_root=project_dir, logger=self.logger)
            geo_ctx = self._context(project_id, "geometry", project_dir,
                                    {"layout_model": layout_model})
            geo_result = geo_agent.run(geo_ctx)
            if not geo_result.success:
                raise RuntimeError("; ".join(geo_result.messages))
            geometry = mp.attach("geometry", "geometry", geo_ctx.task_id,
                                 geo_result.output_model, parent=layout_model)
            self._save(project_dir / "GeometryModel.json", geometry)
            GeometryModel.from_dict(geometry)
            tg.reset_status("geometry", "COMPLETED")
            messages.append(f"Geometry: {len(geometry.get('rooms', []))} 房间 / "
                            f"{len(geometry.get('walls', []))} 墙线")

            # ---- Drawing Agent（Geometry -> Drawing + CAD Mock）----
            drawing_payload = DrawingAgent.build_drawing_model(geometry)
            drawing = mp.attach("drawing", "drawing", f"drawing-{project_id}",
                                drawing_payload, parent=geometry)
            self._save(project_dir / "DrawingModel.json", drawing)
            DrawingModel.from_dict(drawing)

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

            # ---- Professional Validator（§5）----
            val_agent = ProfessionalValidator()
            val_ctx = self._context(
                project_id, "validator", project_dir,
                {"layout_model": layout_model,
                 "professional_models": professional_models})
            val_result = val_agent.run(val_ctx)
            if not val_result.success:
                raise RuntimeError("; ".join(val_result.messages))
            report = mp.attach("validation", "validator", val_ctx.task_id,
                               val_result.output_model, parent=layout_model)
            self._save(project_dir / "ValidationReport.json", report)
            tg.reset_status("validation", "COMPLETED")
            messages.append(f"Validation: {report.get('status', '?')}")

            # ---- GeneratedModel（CAD 执行结果摘要）----
            generated_payload = {
                "source_project_id": project_id,
                "drawing_model_ref": "DrawingModel.json",
                "cad_backend": self.backend,
                "command_count": command_count,
                "drawing_command_log": "drawing_command_log.json",
                "professional_models": list(professional_models.keys()),
                "validation_status": report.get("status"),
                "summary": {"status": "MOCK_EXECUTED", "messages": messages},
            }
            generated = mp.attach("generated", "pipeline",
                                  f"generated-{project_id}",
                                  generated_payload, parent=drawing)
            self._save(project_dir / "GeneratedModel.json", generated)
            GeneratedModel.from_dict(generated)

            # ---- Checkpoint ----
            self._save(project_dir / "model_chain.json", mp.to_dict())
            self._save(project_dir / "task_graph.json", tg.to_dict())
            self._save(project_dir / "project.json",
                       {**project,
                        "pipeline": {"status": "COMPLETED",
                                     "backend": self.backend,
                                     "stage": "PROFESSIONAL_DEEPENING",
                                     "model_chain": mp.to_dict()}})

            return {
                "project_id": project_id,
                "status": "COMPLETED",
                "project_dir": str(project_dir),
                "professional_models": {
                    n: str(project_dir / AGENT_REGISTRY[n][1])
                    for n in professional_models
                },
                "models": {
                    "layout": str(project_dir / "LayoutModel.json"),
                    "geometry": str(project_dir / "GeometryModel.json"),
                    "drawing": str(project_dir / "DrawingModel.json"),
                    "generated": str(project_dir / "GeneratedModel.json"),
                    "validation": str(project_dir / "ValidationReport.json"),
                },
                "drawing_command_log": str(project_dir / "drawing_command_log.json"),
                "model_chain": str(project_dir / "model_chain.json"),
                "command_count": command_count,
                "backend": self.backend,
                "validation_status": report.get("status"),
                "messages": messages,
            }
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"[professional] 执行失败：{e}")
            self._save(project_dir / "model_chain.json", mp.to_dict())
            self._save(project_dir / "task_graph.json", tg.to_dict())
            return {
                "project_id": project_id,
                "status": "FAILED",
                "project_dir": str(project_dir),
                "error": str(e),
                "messages": messages,
            }

    # ------------------------------------------------------------------ #
    def _run_professional(self, layout_model: Dict[str, Any],
                          project_id: str,
                          project_dir: Path) -> Dict[str, Any]:
        """并行执行全部专业 Agent（线程池）。

        注意：Agent 的实际派生工作并行进行；版本打标（mp.attach）在返回后
        串行完成，以保证 ModelPipeline 的版本链线程安全。
        """
        raw: Dict[str, Any] = {}

        def _run_one(agent_name: str):
            cls, _ = AGENT_REGISTRY[agent_name]
            agent = cls()
            ctx = AgentContext(
                project_id=project_id,
                task_id=f"{agent_name}-{project_id}",
                stage="PROFESSIONAL_DEEPENING",
                inputs={"layout_model": layout_model},
                workspace=str(project_dir),
            )
            res = agent.run(ctx)
            if not res.success:
                raise RuntimeError(f"{agent_name}: " + "; ".join(res.messages))
            return agent_name, res.output_model

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(_run_one, n): n for n in AGENT_REGISTRY}
            for fut in futures:
                name, out = fut.result()
                raw[name] = out
        return raw

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
