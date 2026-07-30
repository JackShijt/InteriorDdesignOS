"""
InteriorDesignOS · FlooringRuleEngine（Phase 5.1 §9，Mock Logic）

地面专业规则层：LayoutModel -> FlooringModel（无 IO / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.flooring.flooring_model import FlooringModel

_TILE_ROOM_TYPES = {"KITCHEN", "BATHROOM", "TOILET", "BALCONY"}


class FlooringRuleEngine(BaseRuleEngine):
    """地面专业规则引擎（Mock）。"""

    discipline = "flooring"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> FlooringModel:
        areas: List[Dict[str, Any]] = []
        materials: List[Dict[str, Any]] = []
        patterns: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []
        used: set[str] = set()

        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            is_tile = str(room.get("type", "")).upper() in _TILE_ROOM_TYPES
            material = "tile" if is_tile else "wood_floor"
            used.add(material)
            areas.append({
                "id": f"FA-{rid}", "room_id": rid,
                "name": f"{name}地面区域",
                "spec": {"material": material,
                         "area_m2": room.get("area", 0)},
            })
            patterns.append({
                "id": f"FP-{rid}", "room_id": rid,
                "name": f"{name}铺贴方式",
                "spec": {"pattern": "straight" if is_tile else "staggered"},
            })
            if is_tile:
                constraints.append({
                    "type": "waterproof", "room_id": rid,
                    "description": f"{name}地面须做防水并向地漏找坡（Mock 约束）",
                })
        for i, m in enumerate(sorted(used), start=1):
            materials.append({
                "id": f"FM-{i}", "name": m,
                "spec": {"category": m, "slip_resistance": "R9"},
            })
        return FlooringModel(areas=areas, materials=materials,
                             patterns=patterns, constraints=constraints)


__all__ = ["FlooringRuleEngine"]
