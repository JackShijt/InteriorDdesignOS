"""
InteriorDesignOS · CeilingRuleEngine（Phase 5.1 §9，Mock Logic）

吊顶专业规则层：LayoutModel -> CeilingModel（无 IO / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.ceiling.ceiling_model import CeilingModel


class CeilingRuleEngine(BaseRuleEngine):
    """吊顶专业规则引擎（Mock）。"""

    discipline = "ceiling"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> CeilingModel:
        regions: List[Dict[str, Any]] = []
        levels: List[Dict[str, Any]] = []
        materials: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            regions.append({
                "id": f"CR-{rid}", "room_id": rid,
                "name": f"{name}吊顶区域",
                "spec": {"shape": "flat", "note": "Mock 区域，不含几何"},
            })
            levels.append({
                "id": f"LV-{rid}", "room_id": rid,
                "name": f"{name}标高层级",
                "spec": {"drop_mm": 120, "level": 1},
            })
            constraints.append({
                "type": "clearance", "room_id": rid,
                "description": f"{name}吊顶完成面净高不低于规范要求（Mock 约束）",
            })
        materials.append({
            "id": "CM-1", "name": "石膏板",
            "spec": {"fire_rating": "A", "thickness_mm": 9.5},
        })
        return CeilingModel(ceiling_regions=regions, levels=levels,
                            materials=materials, constraints=constraints)


__all__ = ["CeilingRuleEngine"]
