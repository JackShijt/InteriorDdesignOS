"""DrawingAgent（Phase 6 §6）— 图纸生成代理。

职责边界（本阶段关键约束）：
    DrawingAgent 不知道任何 CAD 实现。
    它只把 DrawingModel（+ 可选 GeometryModel）翻译成 DrawingCommandQueue，
    再交给 CADSession + 注入的 CADAdapter 执行（默认 mock 后端）。

数据流（与 Phase 5.1 一致）：
    DrawingModel → Agent 构建命令队列 → CADSession.run(queue)
                 → CADAdapter（mock/autocad）→ drawing_command_log.json
    Agent 输出经 ArtifactManager 落盘，路径回填 context.outputs。

依赖规则：agents 可依赖 core / cad；禁止依赖 runtime / orchestrator。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.artifact import ArtifactManager
from core.context import AgentContext, BaseAgent, Result, make_metadata
from core.logging import build_logger

from cad import (CADSession, DrawingCommandQueue, build_cad_backend,
                 CreateLayerCommand, CreateTextCommand, DimensionCommand,
                 DoorCommand, FurnitureCommand, InsertBlockCommand,
                 WallCommand, WindowCommand)
from cad.validator import CADValidator, CADValidationError
from models.drawing import DrawingModel


def _pt(p: Any) -> Any:
    """坐标归一：dict {x,y} / list [x,y] -> [x, y]（命令层使用列表坐标）。"""
    if p is None:
        return None
    if isinstance(p, dict):
        return [p.get("x"), p.get("y")]
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return [p[0], p[1]]
    return None


EXAMPLE_DRAWING = Path(__file__).resolve().parents[2] / \
    "schemas" / "examples" / "DrawingModel.example.json"
EXAMPLE_GEOMETRY = Path(__file__).resolve().parents[2] / \
    "schemas" / "examples" / "GeometryModel.example.json"


class DrawingAgent(BaseAgent):
    agent_name = "drawing"
    version = "1.0"

    def __init__(self, workspace_root: Optional[Path] = None,
                 backend: Optional[str] = None, cad_config: Optional[Dict[str, Any]] = None,
                 logger: Any = None):
        """
        DrawingAgent 不知道任何 CAD 实现（含 AutoCAD）。
        依赖链：DrawingModel → DrawingCommandQueue → CADSession → CADAdapter。
        AutoCADAdapter 由 CAD_BACKENDS 插件机制按名加载，Agent 永不 import 它。

        Args:
            workspace_root: 仓库 workspace/ 根目录（落盘历史）。
            backend: CAD 后端名（mock / autocad）；缺省时从 cad_config 取，再兜底 mock。
            cad_config: 运行时配置 dict（config/runtime.yaml 的 cad / autocad 段）。
                AutoCAD 连接参数（host/port/timeout）经此注入，禁止代码写死。
            logger: 可选注入日志器。
        """
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self.cad_config = cad_config or {}
        self.backend = (backend
                        or self.cad_config.get("cad", {}).get("backend", "mock"))
        self.logger = logger or build_logger()

    # ------------------------------------------------------------------ #
    # 入口
    # ------------------------------------------------------------------ #
    def run(self, context: AgentContext) -> Result:
        try:
            drawing_model = self._load_drawing_model(context)
            geometry_model = self._load_geometry_model(context)

            # §8 校验：模型层（图层 / 实体）
            CADValidator.assert_valid(model=drawing_model)

            # 构建命令队列
            queue = self._build_queue(drawing_model, geometry_model)

            # §8 校验：命令层
            CADValidator.assert_valid(commands=list(queue))

            # 执行（经 CADSession + 注入的 CADAdapter；Agent 不直接操作 CAD）
            workspace = self._resolve_workspace(context)
            adapter = build_cad_backend(self.backend, config=self.cad_config,
                                        output_dir=workspace)
            session = CADSession(adapter)
            session.open(context.project_id)
            try:
                session.run(queue)
                log = adapter.export()
            finally:
                session.close()

            return self._publish(context, workspace, drawing_model, queue, log)
        except CADValidationError as e:
            return Result(success=False,
                          messages=[f"CAD 校验失败：{e}"])
        except Exception as e:  # noqa: BLE001 — 统一转为失败 Result
            return Result(success=False, messages=[f"DrawingAgent 失败：{e}"])

    # ------------------------------------------------------------------ #
    # 模型加载
    # ------------------------------------------------------------------ #
    def _load_drawing_model(self, context: AgentContext) -> Dict[str, Any]:
        if context.inputs.get("drawing_model"):
            return context.inputs["drawing_model"]
        path = (context.inputs.get("drawing_model_path")
                or context.parameters.get("model")
                or (context.input_refs[0] if context.input_refs else None)
                or EXAMPLE_DRAWING)
        return self._read_json(path)

    def _load_geometry_model(self, context: AgentContext) -> Optional[Dict[str, Any]]:
        if context.inputs.get("geometry_model"):
            return context.inputs["geometry_model"]
        path = (context.inputs.get("geometry_model_path")
                or context.parameters.get("geometry")
                or EXAMPLE_GEOMETRY)
        try:
            return self._read_json(path)
        except Exception:
            return None

    @staticmethod
    def _read_json(path: Any) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"模型文件不存在：{p}")
        return json.loads(p.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ #
    # Geometry → Drawing 适配器（Phase 8 §4）
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_drawing_model(geometry_model: Dict[str, Any]) -> Dict[str, Any]:
        """GeometryModel -> DrawingModel（生成 layers / entities / dimensions）。
        禁止：直接调用 AutoCAD（纯几何 / 图层转换）。
        """
        geom = geometry_model or {}
        layers = [
            {"name": "WALL", "color": 7, "line_type": "Continuous", "description": "墙体"},
            {"name": "DOOR", "color": 3, "line_type": "Continuous", "description": "门"},
            {"name": "WIN", "color": 4, "line_type": "Continuous", "description": "窗"},
            {"name": "FURN", "color": 2, "line_type": "Continuous", "description": "家具"},
            {"name": "AXIS", "color": 1, "line_type": "Center", "description": "轴线"},
            {"name": "DIM", "color": 1, "line_type": "Continuous", "description": "尺寸标注"},
            {"name": "TITLEBLOCK", "color": 7, "line_type": "Continuous", "description": "图框"},
        ]
        entities: List[Dict[str, Any]] = []
        for w in geom.get("walls", []):
            s, e = w.get("start"), w.get("end")
            pts = [s, e] if (s and e) else w.get("points")
            entities.append({
                "entity_id": w.get("id") or "WALL", "type": "WALL", "layer": "WALL",
                "points": pts, "thickness": w.get("thickness", 200),
                "properties": {"wall_type": w.get("type", "interior")},
            })
        for d in geom.get("doors", []):
            entities.append({
                "entity_id": d.get("id") or "DOOR", "type": "DOOR", "layer": "DOOR",
                "start": _pt(d.get("start")), "end": _pt(d.get("end")),
                "width": d.get("width", 900), "swing": d.get("swing", 90),
            })
        for wd in geom.get("windows", []):
            entities.append({
                "entity_id": wd.get("id") or "WIN", "type": "WINDOW", "layer": "WIN",
                "start": _pt(wd.get("start")), "end": _pt(wd.get("end")),
                "offset": wd.get("offset", 60),
            })
        for f in geom.get("furniture", []):
            entities.append({
                "entity_id": f.get("item_id") or f.get("id") or "FURN",
                "type": "FURNITURE", "layer": "FURN",
                "geometry_ref": f.get("type", "FURNITURE"),
                "position": f.get("position"), "scale": f.get("scale", 1.0),
                "rotation": f.get("rotation", 0.0),
            })
        annotations: List[Dict[str, Any]] = []
        for r in geom.get("rooms", []):
            c = r.get("centroid")
            if c:
                annotations.append({
                    "text": f"{r.get('name', '')} {r.get('area', '')}㎡",
                    "position": [c.get("x"), c.get("y")], "layer": "AXIS", "height": 300,
                })
        dimensions = []
        for r in geom.get("rooms", []):
            b = r.get("boundary", {})
            pts = b.get("points") or []
            if len(pts) >= 2:
                xs = [p["x"] for p in pts]
                ys = [p["y"] for p in pts]
                x0, x1 = min(xs), max(xs)
                y0 = min(ys)
                dimensions.append({
                    "dimension_id": f"DIM-{r.get('room_id', 'R')}",
                    "start": [x0, y0], "end": [x1, y0],
                    "value": round(x1 - x0, 1), "unit": "mm", "layer": "DIM",
                })
        titleblock = {
            "template_ref": "A3", "size": "A3", "author": "InteriorDesignOS",
            "drawing_no": geom.get("geometry_model_version") or "v1",
        }
        sheets = [{"sheet_id": "S1", "name": "平面布置图", "scale": "1:50", "paper_size": "A3"}]
        rooms_meta = [
            {"room_id": r.get("room_id"), "name": r.get("name"),
             "type": r.get("type"), "area": r.get("area")}
            for r in geom.get("rooms", [])
        ]
        return DrawingModel(
            rooms=rooms_meta, layers=layers, entities=entities,
            dimensions=dimensions, annotations=annotations, sheets=sheets,
            blocks=[], titleblock=titleblock,
            coordinate_system=geom.get("coordinate_system", "mm"),
            units=geom.get("units", "mm"),
        ).to_dict()

    # ------------------------------------------------------------------ #
    # 命令队列构建（DrawingModel → DrawingCommand）
    # ------------------------------------------------------------------ #
    def _build_queue(self, drawing_model: Dict[str, Any],
                     geometry_model: Optional[Dict[str, Any]]
                     ) -> DrawingCommandQueue:
        queue: DrawingCommandQueue = DrawingCommandQueue()
        geom = self._index_geometry(geometry_model)

        # 1) 图层
        for layer in drawing_model.get("layers", []) or []:
            name = layer.get("name")
            queue.append(CreateLayerCommand(
                name, layer.get("color", 7),
                layer.get("line_type", "Continuous")))

        # 2) 实体 → 领域命令
        for entity in drawing_model.get("entities", []) or []:
            cmd = self._entity_to_command(entity, geom)
            if cmd is not None:
                queue.append(cmd)

        # 3) 尺寸
        for dim in drawing_model.get("dimensions", []) or []:
            if dim.get("start") and dim.get("end"):
                queue.append(DimensionCommand(
                    dim.get("dimension_id", "DM"), dim["start"], dim["end"],
                    dim.get("value"), dim.get("unit", "mm"),
                    dim.get("layer", "DIM")))

        # 4) 文字标注
        for ann in drawing_model.get("annotations", []) or []:
            if ann.get("position"):
                queue.append(CreateTextCommand(
                    ann.get("text", ""), ann["position"], 300,
                    ann.get("layer")))

        # 5) 块
        for blk in drawing_model.get("blocks", []) or []:
            ref = blk.get("block_ref") or blk.get("name")
            if ref:
                queue.append(InsertBlockCommand(
                    ref, blk.get("position") or [0, 0],
                    blk.get("scale", 1.0), blk.get("rotation", 0.0),
                    blk.get("layer")))

        # 6) 图框
        tb = drawing_model.get("titleblock")
        if tb and tb.get("template_ref"):
            queue.append(InsertBlockCommand(
                tb["template_ref"], [0, 0], 1.0, 0.0, "TITLEBLOCK"))
        return queue

    def _entity_to_command(self, entity: Dict[str, Any],
                           geom: Optional[Dict[str, Any]]):
        etype = entity.get("type")
        eid = entity.get("entity_id", etype)
        layer = entity.get("layer")
        start, end, points, position = self._resolve_geometry(entity, geom)

        if etype == "WALL":
            pts = points or ([start, end] if start and end else None)
            if pts:
                return WallCommand(eid, pts,
                                   thickness=entity.get("thickness", 100),
                                   layer=layer or "WALL")
        if etype == "DOOR" and start and end:
            return DoorCommand(eid, start, end,
                                width=entity.get("width", 900),
                                swing=entity.get("swing", 90),
                                layer=layer or "DOOR")
        if etype == "WINDOW" and start and end:
            return WindowCommand(eid, start, end,
                                 offset=entity.get("offset", 60),
                                 layer=layer or "WIN")
        if etype == "FURNITURE":
            pos = position or (points[0] if points else [0, 0])
            return FurnitureCommand(eid, entity.get("geometry_ref") or eid,
                                    pos, scale=entity.get("scale", 1.0),
                                    rotation=entity.get("rotation", 0.0),
                                    layer=layer or "FURN")
        return None

    # ------------------------------------------------------------------ #
    # 几何解析
    # ------------------------------------------------------------------ #
    @staticmethod
    def _index_geometry(geometry_model: Optional[Dict[str, Any]]
                        ) -> Optional[Dict[str, Any]]:
        if not geometry_model:
            return None
        return {
            "lines": {l.get("id"): l for l in geometry_model.get("lines", [])},
            "polygons": {p.get("id"): p for p in geometry_model.get("polygons", [])},
            "dims": {d.get("id"): d for d in geometry_model.get("dimensions", [])},
        }

    @staticmethod
    def _resolve_geometry(entity: Dict[str, Any],
                          geom: Optional[Dict[str, Any]]):
        ref = entity.get("geometry_ref")
        start = end = points = position = None
        if geom and ref:
            line = geom["lines"].get(ref)
            poly = geom["polygons"].get(ref)
            dim = geom["dims"].get(ref)
            if line:
                start, end = line.get("start"), line.get("end")
            elif dim:
                start, end = dim.get("start"), dim.get("end")
            elif poly:
                points = poly.get("vertices")
                position = (points or [None])[0]
        # 实体自带几何优先
        if entity.get("start") and entity.get("end"):
            start, end = entity["start"], entity["end"]
        if entity.get("points"):
            points = entity["points"]
        if entity.get("position"):
            position = entity["position"]
        return start, end, points, position

    # ------------------------------------------------------------------ #
    # 发布
    # ------------------------------------------------------------------ #
    def _resolve_workspace(self, context: AgentContext) -> Path:
        if context.workspace is not None:
            return Path(context.workspace)
        if self._workspace_root:
            return self._workspace_root / "projects" / context.project_id
        return Path.cwd() / "workspace" / "projects" / context.project_id

    def _publish(self, context: AgentContext, workspace: Path,
                 drawing_model: Dict[str, Any], queue: DrawingCommandQueue,
                 log: Dict[str, Any]) -> Result:
        am = ArtifactManager(workspace)
        name = "cad/drawing_command_log.json"
        am.save(name, log)
        out_path = workspace / name
        context.outputs["drawing_command_log"] = str(out_path)
        context.outputs["command_count"] = len(queue)
        context.outputs["backend"] = self.backend

        quality = {
            "confidence": 1.0,
            "quality_score": 100,
            "validation_passed": True,
            "command_count": len(queue),
            "backend": self.backend,
        }
        return Result(
            success=True,
            output_model={
                "metadata": make_metadata(
                    context.project_id, self.agent_name, context.task_id,
                    "COMPLETED", quality),
                "command_count": len(queue),
                "backend": self.backend,
                "log_path": str(out_path),
            },
            messages=[f"Drawing 完成：{len(queue)} 条命令经 "
                      f"{self.backend} 后端执行"],
            quality=quality,
        )


__all__ = ["DrawingAgent"]
