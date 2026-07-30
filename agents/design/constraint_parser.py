"""Constraint Parser（Phase 4 §4）。

读取 OriginalModel，提取空间刚性约束 `ConstraintSet`。

仅抽取已有几何信息；DWG 未含的字段（管井 / 梁 / 柱 / 阳台 / 设备平台等）
留空并在 notes 中标注，待结构图 / 现场补充——不臆造数据。

兼容两种坐标表示：列表 [x, y] 与字典 {"x":, "y":}。
"""
from typing import Any, Dict, List, Optional
from collections import Counter

# 计划坐标（Y 向上）边界方位映射
_EDGE_DIR = {"max_y": "北", "min_y": "南", "max_x": "东", "min_x": "西"}


def _pt(p: Any) -> Optional[Dict[str, float]]:
    """统一坐标：支持 [x, y] 与 {"x":, "y":}。"""
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        try:
            return {"x": float(p[0]), "y": float(p[1])}
        except (TypeError, ValueError):
            return None
    if isinstance(p, dict) and "x" in p and "y" in p:
        try:
            return {"x": float(p["x"]), "y": float(p["y"])}
        except (TypeError, ValueError):
            return None
    return None


def _window_point(win: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if "position" in win:
        return _pt(win["position"])
    s, e = win.get("start"), win.get("end")
    ps, pe = _pt(s), _pt(e)
    if ps and pe:
        return {"x": (ps["x"] + pe["x"]) / 2.0, "y": (ps["y"] + pe["y"]) / 2.0}
    return ps or pe


def _all_points(model: Dict[str, Any]) -> List[Dict[str, float]]:
    pts: List[Dict[str, float]] = []
    for room in model.get("rooms", []):
        for p in room.get("boundary", []):
            pp = _pt(p)
            if pp:
                pts.append(pp)
    for w in model.get("walls", []):
        for p in (w.get("start"), w.get("end")):
            pp = _pt(p)
            if pp:
                pts.append(pp)
    for win in model.get("windows", []):
        pp = _window_point(win)
        if pp:
            pts.append(pp)
    return pts


def _derive_orientation(model: Dict[str, Any]) -> str:
    pts = _all_points(model)
    if not pts:
        return "待现场确认"
    xs = [p["x"] for p in pts]
    ys = [p["y"] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    win_dirs: List[str] = []
    for win in model.get("windows", []):
        mp = _window_point(win)
        if not mp:
            continue
        edges = {
            "max_y": max_y - mp["y"], "min_y": mp["y"] - min_y,
            "max_x": max_x - mp["x"], "min_x": mp["x"] - min_x,
        }
        edge = min(edges, key=edges.get)
        win_dirs.append(_EDGE_DIR[edge])
    if not win_dirs:
        return "待现场确认"
    return Counter(win_dirs).most_common(1)[0][0]


def parse_constraints(original_model: Dict[str, Any]) -> Dict[str, Any]:
    """从 OriginalModel 提取 ConstraintSet。

    Args:
        original_model: Parser 产出的 OriginalModel（dict）。
    Returns:
        ConstraintSet（dict），字段见 design_spec.schema.json 的 constraints。
    """
    if not isinstance(original_model, dict):
        raise TypeError("original_model 必须是 dict")

    walls = original_model.get("walls", []) or []
    windows = original_model.get("windows", []) or []
    rooms = original_model.get("rooms", []) or []

    wall_ids = [w.get("id") for w in walls if w.get("id")]

    # 面积合计（仅当房间有 area 字段）
    area = 0.0
    for r in rooms:
        a = r.get("area")
        if isinstance(a, (int, float)):
            area += float(a)

    orientation = _derive_orientation(original_model)

    missing = [k for k in ("pipe_shafts", "beams", "columns", "balconies",
                           "equipment_platforms")
               if not original_model.get(k)]
    notes = ""
    if missing:
        notes = (f"DWG 未含字段（{'/'.join(missing)}）需结构图 / 现场补充；"
                 f"层高按常规 2800mm 假设。")

    return {
        "non_removable_walls": list(wall_ids),
        "load_bearing_walls": list(wall_ids),
        "pipe_shafts": original_model.get("pipe_shafts", []) or [],
        "windows": [w.get("id") for w in windows if w.get("id")],
        "beams": original_model.get("beams", []) or [],
        "columns": original_model.get("columns", []) or [],
        "balconies": original_model.get("balconies", []) or [],
        "equipment_platforms": original_model.get("equipment_platforms", []) or [],
        "ceiling_height_mm": float(original_model.get("ceiling_height_mm", 2800)),
        "area_m2": round(area, 3),
        "orientation": orientation,
        "notes": notes,
    }


__all__ = ["parse_constraints"]
