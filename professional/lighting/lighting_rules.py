"""
InteriorDesignOS · LightingRuleEngine（Phase 5.1 §9，Mock Logic）

照明专业规则层：LayoutModel(+DesignSpec.lighting) -> LightingModel。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.lighting.lighting_model import LightingModel


class LightingRuleEngine(BaseRuleEngine):
    """照明专业规则引擎（Mock）。"""

    discipline = "lighting"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> LightingModel:
        fixtures: List[Dict[str, Any]] = []
        groups: List[Dict[str, Any]] = []
        controls: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        strategy = ""
        if design_spec:
            strategy = (design_spec.get("lighting") or {}).get(
                "artificial_light", "")

        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            fixtures.append({
                "id": f"FX-{rid}", "room_id": rid,
                "name": f"{name}基础照明灯具",
                "spec": {"type": "downlight", "cct": "4000K",
                         "strategy": strategy or "常规照明"},
            })
            groups.append({
                "id": f"G-{rid}", "room_id": rid,
                "name": f"{name}照明分组",
                "spec": {"members": [f"FX-{rid}"]},
            })
            controls.append({
                "id": f"CT-{rid}", "room_id": rid,
                "name": f"{name}控制面板",
                "spec": {"type": "wall_switch", "scenes": ["on", "off"]},
            })
            constraints.append({
                "type": "comfort", "room_id": rid,
                "description": f"{name}照度满足居住舒适要求（Mock 约束）",
            })
        return LightingModel(fixtures=fixtures, groups=groups,
                             controls=controls, constraints=constraints)


__all__ = ["LightingRuleEngine"]
