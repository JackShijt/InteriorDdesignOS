"""
InteriorDesignOS · FurnitureRuleEngine（Phase 5.1 §9，Mock Logic）

家具专业规则层：LayoutModel -> FurnitureModel。
只读引用 LayoutModel.furniture，绝不回写 LayoutModel。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.furniture.furniture_model import FurnitureModel


class FurnitureRuleEngine(BaseRuleEngine):
    """家具专业规则引擎（Mock）。"""

    discipline = "furniture"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> FurnitureModel:
        movable: List[Dict[str, Any]] = []
        fixed: List[Dict[str, Any]] = []
        clearance: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        for item in layout.get("furniture", []) or []:
            fid = item.get("id", "F?")
            movable.append({
                "id": f"MV-{fid}",
                "name": f"活动家具（引用布局家具 {fid}）",
                "spec": {"layout_ref": fid,
                         "category": item.get("category", "GENERIC")},
            })
        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            fixed.append({
                "id": f"FX-{rid}", "room_id": rid,
                "name": f"{name}定制柜体（Mock）",
                "spec": {"type": "built_in_cabinet"},
            })
            clearance.append({
                "id": f"CL-{rid}", "room_id": rid,
                "name": f"{name}通行净宽要求",
                "spec": {"min_passage_mm": 800},
            })
            constraints.append({
                "type": "clearance", "room_id": rid,
                "description": f"{name}主通道净宽不小于 800mm（Mock 约束）",
            })
        return FurnitureModel(movable=movable, fixed=fixed,
                              clearance=clearance, constraints=constraints)


__all__ = ["FurnitureRuleEngine"]
