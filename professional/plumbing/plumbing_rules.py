"""
InteriorDesignOS · PlumbingRuleEngine（Phase 5.1 §9，Mock Logic）

给排水专业规则层：LayoutModel -> PlumbingModel（无 IO / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.plumbing.plumbing_model import PlumbingModel

_WET_ROOM_TYPES = {"KITCHEN", "BATHROOM", "TOILET", "LAUNDRY", "BALCONY"}


class PlumbingRuleEngine(BaseRuleEngine):
    """给排水专业规则引擎（Mock）。"""

    discipline = "plumbing"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> PlumbingModel:
        water_supply: List[Dict[str, Any]] = []
        drain: List[Dict[str, Any]] = []
        equipment: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        wet_rooms = [r for r in layout.get("rooms", []) or []
                     if str(r.get("type", "")).upper() in _WET_ROOM_TYPES]
        rooms = wet_rooms or (layout.get("rooms", []) or [])[:1]

        for room in rooms:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            water_supply.append({
                "id": f"WS-{rid}", "room_id": rid,
                "name": f"{name}给水点",
                "spec": {"pipe": "PPR-DN20", "cold_hot": "both"},
            })
            drain.append({
                "id": f"DR-{rid}", "room_id": rid,
                "name": f"{name}排水点",
                "spec": {"pipe": "PVC-DN50", "slope": "0.026"},
            })
            equipment.append({
                "id": f"EQ-{rid}", "room_id": rid,
                "name": f"{name}用水设备（Mock）",
                "spec": {"type": "generic_fixture"},
            })
            constraints.append({
                "type": "code", "room_id": rid,
                "description": f"{name}排水须设存水弯，防返味（Mock 规范约束）",
            })
        return PlumbingModel(water_supply=water_supply, drain=drain,
                             equipment=equipment, constraints=constraints)


__all__ = ["PlumbingRuleEngine"]
