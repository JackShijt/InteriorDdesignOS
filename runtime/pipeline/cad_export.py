"""runtime.pipeline.cad_export · CAD 导出与 DWG Round-Trip（Phase 12.4 / 12.5）。

数据流（Phase 12 验收链路）：
    DrawingModel
        ↓ translate_drawing_model()   （后端中性实体，不含任何 CAD API）
    CAD Adapter（cad.adapter.resolve_adapter — Pipeline 不知道具体 CAD 软件）
        ↓ export_drawing_to_dwg()
    DWG
        ↓ read_dwg_to_generated_model()
    GeneratedModel
        ↓ round_trip_validate()
    ValidationReport（Compare LayoutModel：房间/墙/门窗数量、坐标误差、尺寸误差）
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cad.adapter import CADAdapter, resolve_adapter
from models.generated import GeneratedModel

# 允许的坐标误差 / 尺寸误差（单位 mm）
DEFAULT_COORD_TOLERANCE = 1.0
DEFAULT_DIM_TOLERANCE = 1.0


# --------------------------------------------------------------------------- #
# 坐标工具
# --------------------------------------------------------------------------- #
def _xy(p: Any) -> Optional[Dict[str, float]]:
    """任意坐标表示 → {"x": float, "y": float}。"""
    if p is None:
        return None
    if isinstance(p, dict):
        return {"x": float(p.get("x", 0)), "y": float(p.get("y", 0))}
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        return {"x": float(p[0]), "y": float(p[1])}
    return None


def _dist(a: Optional[Dict[str, float]], b: Optional[Dict[str, float]]) -> float:
    if not a or not b:
        return float("inf")
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


# --------------------------------------------------------------------------- #
# Phase 12.4 · DrawingModel → 后端中性实体
# --------------------------------------------------------------------------- #
def translate_drawing_model(drawing_model: Dict[str, Any]
                            ) -> Dict[str, List[Dict[str, Any]]]:
    """DrawingModel → 后端中性 layers / entities / dimensions。

    实体映射（不依赖任何具体 CAD 软件）：
        WALL      → polyline（points）
        DOOR/WIN  → line（start/end）
        FURNITURE → block（name/position）
        annotation→ text
    每个实体携带 ``tag``（源 entity_id），供 DWG 回读后与
    LayoutModel 对齐（Round-Trip 验证）。
    """
    dm = drawing_model or {}
    layers = [
        {"name": l.get("name", "0"),
         "color": str(l.get("color", "white")),
         "linetype": l.get("line_type", "CONTINUOUS")}
        for l in dm.get("layers", []) or []
    ]

    entities: List[Dict[str, Any]] = []
    for e in dm.get("entities", []) or []:
        etype = e.get("type")
        tag = e.get("entity_id") or etype
        if etype == "WALL":
            pts = e.get("points") or []
            points = [_xy(p) for p in pts if _xy(p)]
            if len(points) >= 2:
                entities.append({
                    "type": "polyline", "layer": e.get("layer", "WALL"),
                    "points": points, "tag": tag, "role": "wall",
                    "thickness": e.get("thickness", 200),
                })
        elif etype in ("DOOR", "WINDOW"):
            s, t = _xy(e.get("start")), _xy(e.get("end"))
            if s and t:
                entities.append({
                    "type": "line",
                    "layer": e.get("layer", "DOOR" if etype == "DOOR" else "WIN"),
                    "start": s, "end": t, "tag": tag,
                    "role": "door" if etype == "DOOR" else "window",
                    "width": e.get("width"),
                })
        elif etype == "FURNITURE":
            pos = _xy(e.get("position")) or {"x": 0.0, "y": 0.0}
            entities.append({
                "type": "block", "layer": e.get("layer", "FURN"),
                "name": e.get("geometry_ref") or tag, "position": pos,
                "scale": e.get("scale", 1.0), "rotation": e.get("rotation", 0.0),
                "tag": tag, "role": "furniture",
            })

    for ann in dm.get("annotations", []) or []:
        pos = _xy(ann.get("position"))
        if pos:
            entities.append({
                "type": "text", "layer": ann.get("layer", "AXIS"),
                "text": ann.get("text", ""), "position": pos,
                "height": ann.get("height", 300), "role": "annotation",
            })

    dimensions: List[Dict[str, Any]] = []
    for d in dm.get("dimensions", []) or []:
        s, t = _xy(d.get("start")), _xy(d.get("end"))
        if s and t:
            dimensions.append({
                "type": "linear", "layer": d.get("layer", "DIM"),
                "start": s, "end": t, "value": d.get("value"),
                "unit": d.get("unit", "mm"),
                "tag": d.get("dimension_id", "DIM"),
            })

    return {"layers": layers, "entities": entities, "dimensions": dimensions}


# --------------------------------------------------------------------------- #
# Phase 12.4 · DWG 导出（经统一 CAD Adapter）
# --------------------------------------------------------------------------- #
def export_drawing_to_dwg(drawing_model: Dict[str, Any], dwg_path: str,
                          project_id: str = "project",
                          preferred_backend: Optional[str] = None,
                          adapter: Optional[CADAdapter] = None
                          ) -> Dict[str, Any]:
    """DrawingModel → CAD Adapter → DWG Export。

    Pipeline 不知道具体 CAD 软件：后端由 registry + capability 解析，
    首选后端不可用/能力不足时自动降级（默认降级到 mock）。

    返回导出报告：backend / degraded / dwg_path / 各类计数 / skipped。
    """
    neutral = translate_drawing_model(drawing_model)

    degraded, reason = False, ""
    if adapter is None:
        resolved = resolve_adapter(preferred=preferred_backend)
        adapter = resolved["adapter"]
        degraded = resolved["degraded"]
        reason = resolved["reason"]

    skipped: List[str] = []
    adapter.create_document(project_id, metadata={
        "project_id": project_id,
        "drawing_model_version": drawing_model.get("drawing_model_version"),
        "units": drawing_model.get("units", "mm"),
    })
    try:
        for layer in neutral["layers"]:
            adapter.create_layer(layer["name"], layer["color"],
                                 layer["linetype"])
        for entity in neutral["entities"]:
            if not adapter.supports(entity["type"]):
                skipped.append(f"{entity['type']}:{entity.get('tag', '')}")
                continue
            adapter.create_entity(entity)
        for dim in neutral["dimensions"]:
            if not adapter.supports("dimension"):
                skipped.append(f"dimension:{dim.get('tag', '')}")
                continue
            adapter.create_dimension(dim)
        save_info = adapter.save_dwg(dwg_path)
    finally:
        adapter.close()

    return {
        "backend": adapter.backend_name,
        "degraded": degraded,
        "degrade_reason": reason,
        "dwg_path": str(save_info.get("path", dwg_path)),
        "layer_count": len(neutral["layers"]),
        "entity_count": len(neutral["entities"]) - len(
            [s for s in skipped if not s.startswith("dimension:")]),
        "dimension_count": len(neutral["dimensions"]),
        "skipped": skipped,
    }


# --------------------------------------------------------------------------- #
# Phase 12.5 · DWG 回读 → GeneratedModel
# --------------------------------------------------------------------------- #
def read_dwg_to_generated_model(dwg_path: str, project_id: str = "project",
                                backend: Optional[str] = None,
                                adapter: Optional[CADAdapter] = None
                                ) -> Dict[str, Any]:
    """重新读取 DWG → GeneratedModel（dict）。"""
    if adapter is None:
        resolved = resolve_adapter(preferred=backend)
        adapter = resolved["adapter"]
    data = adapter.load_dwg(dwg_path)

    entities = list(data.get("entities", []))
    dimensions = list(data.get("dimensions", []))
    counts = {
        "layers": len(data.get("layers", [])),
        "entities": len(entities),
        "dimensions": len(dimensions),
        "walls": sum(1 for e in entities if e.get("role") == "wall"),
        "doors": sum(1 for e in entities if e.get("role") == "door"),
        "windows": sum(1 for e in entities if e.get("role") == "window"),
        "furniture": sum(1 for e in entities if e.get("role") == "furniture"),
        "annotations": sum(1 for e in entities if e.get("role") == "annotation"),
    }
    model = GeneratedModel(
        source_project_id=project_id,
        cad_backend=data.get("backend", adapter.backend_name),
        dwg_path=str(dwg_path),
        layers=list(data.get("layers", [])),
        entities=entities,
        dimensions=dimensions,
        counts=counts,
        summary={"source": "dwg_round_trip", "counts": counts},
    )
    return model.to_dict()


# --------------------------------------------------------------------------- #
# Phase 12.5 · Round-Trip 验证（Compare LayoutModel）
# --------------------------------------------------------------------------- #
def _index_by_tag(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(i.get("tag")): i for i in items if i.get("tag")}


def _wall_endpoints(entity: Dict[str, Any]
                    ) -> Tuple[Optional[Dict[str, float]],
                               Optional[Dict[str, float]]]:
    pts = entity.get("points") or []
    if len(pts) >= 2:
        return _xy(pts[0]), _xy(pts[-1])
    return _xy(entity.get("start")), _xy(entity.get("end"))


def round_trip_validate(generated_model: Dict[str, Any],
                        layout_model: Dict[str, Any],
                        coord_tolerance: float = DEFAULT_COORD_TOLERANCE,
                        dim_tolerance: float = DEFAULT_DIM_TOLERANCE
                        ) -> Dict[str, Any]:
    """GeneratedModel（DWG 回读）↔ LayoutModel 比对 → ValidationReport。

    验证项（Phase 12.5）：
        房间数量 / 墙数量 / 门窗数量 / 坐标误差 / 尺寸误差
    """
    layout = layout_model or {}
    gen = generated_model or {}
    entities = list(gen.get("entities", []))
    dimensions = list(gen.get("dimensions", []))

    checks: List[Dict[str, Any]] = []

    def _check(name: str, expected: Any, actual: Any, passed: bool,
               detail: str = "") -> None:
        checks.append({"check": name, "expected": expected, "actual": actual,
                       "passed": bool(passed), "detail": detail})

    # 1) 房间数量（每房间一条 DIM-{room_id} 标注 → 双后端均支持 dimension）
    layout_rooms = list(layout.get("rooms", []))
    room_tags = {str(d.get("tag", "")) for d in dimensions
                 if str(d.get("tag", "")).startswith("DIM-")}
    _check("room_count", len(layout_rooms), len(room_tags),
           len(room_tags) == len(layout_rooms))

    # 2) 墙数量
    layout_walls = list(layout.get("walls", []))
    gen_walls = [e for e in entities if e.get("role") == "wall"]
    _check("wall_count", len(layout_walls), len(gen_walls),
           len(gen_walls) == len(layout_walls))

    # 3) 门 / 窗数量
    layout_doors = list(layout.get("doors", []))
    layout_windows = list(layout.get("windows", []))
    gen_doors = [e for e in entities if e.get("role") == "door"]
    gen_windows = [e for e in entities if e.get("role") == "window"]
    _check("door_count", len(layout_doors), len(gen_doors),
           len(gen_doors) == len(layout_doors))
    _check("window_count", len(layout_windows), len(gen_windows),
           len(gen_windows) == len(layout_windows))

    # 4) 坐标误差（按 tag=wall_id/door_id/window_id 对齐，取最大端点偏差）
    gen_by_tag = _index_by_tag(entities)
    max_coord_error, coord_samples = 0.0, 0
    for group, id_key in ((layout_walls, "wall_id"),
                          (layout_doors, "door_id"),
                          (layout_windows, "window_id")):
        for item in group:
            tag = str(item.get(id_key) or item.get("id"))
            ent = gen_by_tag.get(tag)
            if not ent:
                continue
            if ent.get("role") == "wall":
                gs, ge = _wall_endpoints(ent)
            else:
                gs, ge = _xy(ent.get("start")), _xy(ent.get("end"))
            ls, le = _xy(item.get("start")), _xy(item.get("end"))
            if ls and le and gs and ge:
                err = max(_dist(ls, gs), _dist(le, ge))
                max_coord_error = max(max_coord_error, err)
                coord_samples += 1
    _check("coordinate_error", f"<= {coord_tolerance}mm",
           round(max_coord_error, 3),
           coord_samples > 0 and max_coord_error <= coord_tolerance,
           f"compared {coord_samples} elements")

    # 5) 尺寸误差（DIM 标注值 vs start/end 实际距离）
    max_dim_error, dim_samples = 0.0, 0
    for d in dimensions:
        s, e = _xy(d.get("start")), _xy(d.get("end"))
        value = d.get("value")
        if s and e and value is not None:
            err = abs(_dist(s, e) - float(value))
            max_dim_error = max(max_dim_error, err)
            dim_samples += 1
    _check("dimension_error", f"<= {dim_tolerance}mm",
           round(max_dim_error, 3),
           dim_samples > 0 and max_dim_error <= dim_tolerance,
           f"compared {dim_samples} dimensions")

    passed = all(c["passed"] for c in checks)
    return {
        "report_type": "dwg_round_trip",
        "passed": passed,
        "checks": checks,
        "max_coordinate_error_mm": round(max_coord_error, 3),
        "max_dimension_error_mm": round(max_dim_error, 3),
        "compared_against": "LayoutModel",
        "cad_backend": gen.get("cad_backend", "mock"),
        "dwg_path": gen.get("dwg_path", ""),
    }


# --------------------------------------------------------------------------- #
# 一站式：导出 + 回读 + 验证
# --------------------------------------------------------------------------- #
def run_dwg_round_trip(drawing_model: Dict[str, Any],
                       layout_model: Dict[str, Any],
                       dwg_path: str, project_id: str = "project",
                       preferred_backend: Optional[str] = None
                       ) -> Dict[str, Any]:
    """生成 DWG → 回读 DWG → GeneratedModel → ValidationReport。"""
    export_report = export_drawing_to_dwg(
        drawing_model, dwg_path, project_id=project_id,
        preferred_backend=preferred_backend)
    generated = read_dwg_to_generated_model(
        export_report["dwg_path"], project_id=project_id,
        backend=export_report["backend"])
    validation = round_trip_validate(generated, layout_model)
    return {
        "export": export_report,
        "generated_model": generated,
        "validation": validation,
    }


__all__ = [
    "translate_drawing_model",
    "export_drawing_to_dwg",
    "read_dwg_to_generated_model",
    "round_trip_validate",
    "run_dwg_round_trip",
]
