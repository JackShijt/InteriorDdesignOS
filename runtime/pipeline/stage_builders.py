"""
runtime.pipeline.stage_builders · 上游/下游阶段确定性构造器（Phase 11 §5）。

说明（遵守约束）：
  - 本模块**不是**真实装修 / AI 设计算法，也不是 DWG 解析。
  - 仅为 Phase 11 运行时集成演示，从结构化需求确定性地合成模型实例，
    用于闭环验证：Input -> Parser -> Design -> Layout -> ... -> Deliverable。
  - 不修改任何 Schema SSOT；仅生成模型实例（与 Professional/Drawing 的
    “Mock Logic / CAD Mock Export” 同属运行时集成 Mock）。
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from runtime.orchestrator.task_planner import ProjectRequirement


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _meta(version: str = "1.0") -> Dict[str, Any]:
    return {
        "version": version,
        "generated_at": _now_iso(),
        "generator": "phase11-mock-builder",
    }


# --------------------------------------------------------------------------
# 1) Mock Parser：结构化需求 -> OriginalModel（非 DWG 解析）
# --------------------------------------------------------------------------
def build_original_model(requirement: ProjectRequirement) -> Dict[str, Any]:
    rooms = requirement.rooms or []
    spaces = [
        {"name": r.get("name", f"room-{i}"),
         "type": r.get("type", "ROOM"),
         "area": float(r.get("area", 0.0))}
        for i, r in enumerate(rooms)
    ]
    quality_rooms = len(rooms)
    return {
        "metadata": _meta(),
        "version": "1.0",
        "source_type": "TEXT",
        "source_path": requirement.source or "user-requirement",
        "quality": {
            "score": round(min(1.0, 0.4 + 0.05 * quality_rooms), 2),
            "walls": quality_rooms * 4,
            "doors": quality_rooms,
            "windows": quality_rooms,
            "rooms": quality_rooms,
        },
        "rooms": rooms,
        "spaces": spaces,
        "story": requirement.story or 1,
    }


# --------------------------------------------------------------------------
# 2) Mock Design：OriginalModel + 需求 -> DesignSpec
# --------------------------------------------------------------------------
def build_design_spec(original_model: Dict[str, Any],
                      requirement: ProjectRequirement) -> Dict[str, Any]:
    spaces = [
        {
            "name": s.get("name", "space"),
            "type": s.get("type", "ROOM"),
            "area": float(s.get("area", 0.0)),
            "requirements": requirement.features or [],
        }
        for s in original_model.get("spaces", [])
    ]
    return {
        "metadata": _meta(),
        "version": "1.0",
        "style": requirement.style or "现代简约",
        "spaces": spaces,
        "materials": {
            "floor": requirement.materials.get("floor", "木地板")
            if requirement.materials else "木地板",
            "wall": "乳胶漆",
        },
        "requirements": requirement.features or [],
    }


# --------------------------------------------------------------------------
# 3) Mock Layout：DesignSpec -> LayoutModel（确定性网格布置，非 AI 算法）
# --------------------------------------------------------------------------
_FURNITURE_BY_TYPE = {
    "LIVING": ("沙发", "SOFA"),
    "BEDROOM": ("床", "BED"),
    "KITCHEN": ("橱柜", "CABINET"),
    "BATHROOM": ("马桶", "TOILET"),
    "BALCONY": ("晾衣架", "RACK"),
    "DINING": ("餐桌", "TABLE"),
    "STUDY": ("书桌", "DESK"),
    "ENTRY": ("鞋柜", "SHOE_CABINET"),
    "ROOM": ("家具", "FURNITURE"),
}


def build_layout_model(design_spec: Dict[str, Any],
                        requirement: ProjectRequirement) -> Dict[str, Any]:
    area = float(requirement.area or 100.0)
    side_m = math.sqrt(area)
    side_mm = side_m * 1000.0

    spaces = design_spec.get("spaces", []) or [
        {"name": "空间", "type": "ROOM", "area": area}
    ]
    n = len(spaces)
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = max(1, math.ceil(n / cols))
    cell_w = side_mm / cols
    cell_h = side_mm / rows

    rooms: List[Dict[str, Any]] = []
    for i, sp in enumerate(spaces):
        col = i % cols
        row = i // cols
        x0 = col * cell_w
        y0 = row * cell_h
        pad = min(cell_w, cell_h) * 0.05
        x1 = x0 + cell_w - pad
        y1 = y0 + cell_h - pad
        rtype = str(sp.get("type", "ROOM")).upper()
        furn_name, furn_type = _FURNITURE_BY_TYPE.get(rtype, _FURNITURE_BY_TYPE["ROOM"])
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        room_id = f"R{i + 1:02d}"
        # 坐标统一使用 {"x":, "y":} 字典格式（与专业 Agent / Validator 约定一致）
        pts = [{"x": x0, "y": y0}, {"x": x1, "y": y0},
               {"x": x1, "y": y1}, {"x": x0, "y": y1}]
        rooms.append({
            "room_id": room_id,
            "name": sp.get("name", room_id),
            "type": rtype,
            "boundary": {
                "type": "rectangle",
                "points": pts,
            },
            "area": round((x1 - x0) * (y1 - y0) / 1e6, 2),
            "wall_thickness": 200,
            "floor_height": 2800,
            "furniture": [{
                "id": f"{room_id}-F1",
                "name": furn_name,
                "type": furn_type,
                "position": {"x": cx, "y": cy},
                "size": [min(2000.0, cell_w * 0.4), min(1000.0, cell_h * 0.4)],
                "rotation": 0,
            }],
        })

    # 墙体/门/窗/动线：从房间外框派生最小集合（确定性）
    walls = []
    doors = []
    windows = []
    edges = 0
    for r in rooms:
        pts = r["boundary"]["points"]
        for k in range(len(pts)):
            a = pts[k]
            b = pts[(k + 1) % len(pts)]
            edges += 1
            walls.append({"id": f"W{edges:03d}",
                          "start": {"x": a["x"], "y": a["y"]},
                          "end": {"x": b["x"], "y": b["y"]},
                          "thickness": 200})
        # 门：位于底边中点（含 start/end 线段，供 Geometry/Drawing/DWG 链路使用）
        door_cx = (pts[0]["x"] + pts[1]["x"]) / 2
        door_cy = (pts[0]["y"] + pts[1]["y"]) / 2
        doors.append({"id": f"D{len(doors) + 1:03d}",
                      "position": {"x": door_cx, "y": door_cy},
                      "start": {"x": door_cx - 450.0, "y": door_cy},
                      "end": {"x": door_cx + 450.0, "y": door_cy},
                      "width": 900})
        # 窗：位于右边中点（竖直线段）
        win_cx = (pts[1]["x"] + pts[2]["x"]) / 2
        win_cy = (pts[1]["y"] + pts[2]["y"]) / 2
        windows.append({"id": f"WIN{len(windows) + 1:03d}",
                        "position": {"x": win_cx, "y": win_cy},
                        "start": {"x": win_cx, "y": win_cy - 750.0},
                        "end": {"x": win_cx, "y": win_cy + 750.0},
                        "width": 1500})

    return {
        "metadata": _meta(),
        "version": "1.0",
        "bounds": {"width": side_mm, "height": side_mm},
        "rooms": rooms,
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "circulation": [r["room_id"] for r in rooms],
    }


# --------------------------------------------------------------------------
# 4) Deliverable 装配（运行时集成，非真实 CAD 导出）
# --------------------------------------------------------------------------
def build_deliverable(
    *,
    project_id: str,
    requirement: ProjectRequirement,
    artifacts: Dict[str, Any],
    professional_models: Dict[str, Any],
    validation_report: Dict[str, Any],
    generated_model: Dict[str, Any],
    cad_command_count: int,
) -> Dict[str, Any]:
    summary = {
        "project_id": project_id,
        "name": requirement.name,
        "disciplines": list(professional_models.keys()),
        "rooms": len(artifacts.get("LAYOUT", {}).get("rooms", [])),
        "cad_commands": cad_command_count,
        "conflict_count": len(validation_report.get("conflicts", [])),
        "validation_passed": bool(validation_report.get("passed", False)),
        "generated_at": _now_iso(),
    }
    return {
        "deliverable_id": f"{project_id}-DELIVERABLE",
        "project_id": project_id,
        "generated_at": _now_iso(),
        "status": "DELIVERED",
        "summary": summary,
        "components": {
            "original_model": artifacts.get("ORIGINAL_MODEL"),
            "design_spec": artifacts.get("DESIGN_SPEC"),
            "layout_model": artifacts.get("LAYOUT"),
            "professional_models": professional_models,
            "geometry_model": artifacts.get("GEOMETRY"),
            "drawing_model": artifacts.get("DRAWING"),
            "validation_report": validation_report,
            "generated_model": generated_model,
        },
    }


__all__ = [
    "build_original_model",
    "build_design_spec",
    "build_layout_model",
    "build_deliverable",
]
