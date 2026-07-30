"""agents.geometry · Layout → Geometry 适配器（Phase 8 §3）。

输入 LayoutModel，输出 GeometryModel。
职责：坐标转换 / 房间边界转换 / 墙线生成 / 家具定位转换。
禁止：生成 DWG（不调用任何 CAD 后端）。
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.context import AgentContext, BaseAgent, Result
from core.logging import build_logger
from models.geometry import GeometryModel


def _scale_point(p: Any, s: float) -> Optional[Dict[str, float]]:
    if p is None:
        return None
    if isinstance(p, dict):
        x = p.get("x", 0)
        y = p.get("y", 0)
        return {"x": round(float(x) * s, 2), "y": round(float(y) * s, 2)}
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return {"x": round(float(p[0]) * s, 2), "y": round(float(p[1]) * s, 2)}
    return None


class GeometryAgent(BaseAgent):
    agent_name = "geometry"
    version = "1.0"

    def __init__(self, workspace_root=None, logger=None):
        self._workspace_root = Path(workspace_root) if workspace_root else None
        self.logger = logger or build_logger()

    def run(self, context: AgentContext) -> Result:
        try:
            layout = self._load_layout(context)
            payload = self._transform(layout, context)
            return Result(
                success=True,
                output_model=payload,
                messages=[f"GeometryAgent 完成：{len(payload.get('rooms', []))} 房间 / "
                          f"{len(payload.get('walls', []))} 墙线 / "
                          f"{len(payload.get('furniture', []))} 家具"],
            )
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"GeometryAgent 失败：{e}")
            return Result(success=False, messages=[f"GeometryAgent 失败：{e}"])

    def _load_layout(self, context: AgentContext) -> Dict[str, Any]:
        lm = context.inputs.get("layout_model")
        if isinstance(lm, dict):
            return lm
        path = context.inputs.get("layout_model_path")
        if not path and context.input_refs:
            path = context.input_refs[0]
        if path:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        raise ValueError("GeometryAgent 缺少 LayoutModel 输入")

    def _transform(self, layout: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        params = context.parameters or {}
        scale = float(params.get("scale", 1.0))
        coord = params.get("coordinate_system", "mm")
        rooms = self._transform_rooms(layout, scale)
        walls = self._transform_walls(layout, scale)
        furniture = self._transform_furniture(layout, scale)
        doors = self._transform_doors(layout, scale)
        windows = self._transform_windows(layout, scale)
        dimensions = self._transform_dimensions(rooms)
        return GeometryModel(
            rooms=rooms, walls=walls, furniture=furniture, doors=doors,
            windows=windows, coordinate_system=coord, units=coord,
            dimensions=dimensions,
        ).to_dict()

    def _transform_rooms(self, layout, scale):
        out = []
        for r in layout.get("rooms", []):
            b = r.get("boundary", {}) or {}
            pts = b.get("points", []) or []
            sp = [_scale_point(p, scale) for p in pts]
            area = r.get("area")
            if area is None and len(sp) >= 3:
                area = round(self._polygon_area(sp) / 1e6, 2)
            perimeter = r.get("perimeter")
            if perimeter is None and len(sp) >= 3:
                perimeter = round(self._polygon_perimeter(sp) / 1000, 2)
            centroid = r.get("centroid")
            if centroid is None and len(sp) >= 3:
                centroid = self._polygon_centroid(sp)
            out.append({
                "room_id": r.get("room_id") or r.get("name"),
                "name": r.get("name"),
                "type": r.get("type", "room"),
                "boundary": {"type": b.get("type", "polygon"), "points": sp},
                "area": area,
                "perimeter": perimeter,
                "centroid": centroid,
                "floor_finish": r.get("floor_finish"),
            })
        return out

    def _transform_walls(self, layout, scale):
        out = []
        for w in layout.get("walls", []):
            out.append({
                "id": w.get("wall_id") or w.get("id"),
                "start": _scale_point(w.get("start"), scale),
                "end": _scale_point(w.get("end"), scale),
                "thickness": w.get("thickness", 200),
                "type": w.get("type", "interior"),
                "layer": w.get("layer", "WALL"),
            })
        return out

    def _transform_furniture(self, layout, scale):
        out = []
        for f in layout.get("furniture", []):
            out.append({
                "item_id": f.get("item_id") or f.get("id"),
                "name": f.get("name"),
                "type": f.get("type", "FURNITURE"),
                "position": _scale_point(f.get("position"), scale),
                "size": f.get("size"),
                "rotation": f.get("rotation", 0.0),
                "scale": scale,
            })
        return out

    def _transform_doors(self, layout, scale):
        out = []
        for d in layout.get("doors", []):
            out.append({
                "id": d.get("door_id") or d.get("id"),
                "start": _scale_point(d.get("start"), scale),
                "end": _scale_point(d.get("end"), scale),
                "width": d.get("width", 900),
                "swing": d.get("swing", 90),
                "layer": d.get("layer", "DOOR"),
                "type": d.get("type", "single"),
            })
        return out

    def _transform_windows(self, layout, scale):
        out = []
        for wd in layout.get("windows", []):
            out.append({
                "id": wd.get("window_id") or wd.get("id"),
                "start": _scale_point(wd.get("start"), scale),
                "end": _scale_point(wd.get("end"), scale),
                "width": wd.get("width", 1500),
                "offset": wd.get("offset", 60),
                "layer": wd.get("layer", "WIN"),
            })
        return out

    def _transform_dimensions(self, rooms):
        out = []
        for r in rooms:
            b = r.get("boundary", {})
            pts = b.get("points", [])
            if len(pts) < 2:
                continue
            xs = [p["x"] for p in pts]
            ys = [p["y"] for p in pts]
            x0, x1 = min(xs), max(xs)
            y0 = min(ys)
            out.append({
                "dimension_id": f"DIM-{r.get('room_id', 'R')}",
                "start": [x0, y0], "end": [x1, y0],
                "value": round(x1 - x0, 1), "unit": "mm", "layer": "DIM",
            })
        return out

    @staticmethod
    def _polygon_area(pts):
        s = 0.0
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]["x"], pts[i]["y"]
            x2, y2 = pts[(i + 1) % n]["x"], pts[(i + 1) % n]["y"]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2.0

    @staticmethod
    def _polygon_perimeter(pts):
        s = 0.0
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]["x"], pts[i]["y"]
            x2, y2 = pts[(i + 1) % n]["x"], pts[(i + 1) % n]["y"]
            s += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        return s

    @staticmethod
    def _polygon_centroid(pts):
        a = 0.0
        cx = 0.0
        cy = 0.0
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]["x"], pts[i]["y"]
            x2, y2 = pts[(i + 1) % n]["x"], pts[(i + 1) % n]["y"]
            cross = x1 * y2 - x2 * y1
            a += cross
            cx += (x1 + x2) * cross
            cy += (y1 + y2) * cross
        a *= 0.5
        if abs(a) < 1e-9:
            return {"x": sum(p["x"] for p in pts) / n, "y": sum(p["y"] for p in pts) / n}
        return {"x": round(cx / (6 * a), 2), "y": round(cy / (6 * a), 2)}
