"""
InteriorDesignOS · HVACRuleEngine（Phase 5.1 §9，Mock Logic）

暖通专业规则层：LayoutModel -> HVACModel（无 IO / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.hvac.hvac_model import HVACModel


class HVACRuleEngine(BaseRuleEngine):
    """暖通专业规则引擎（Mock）。"""

    discipline = "hvac"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> HVACModel:
        air_supply: List[Dict[str, Any]] = []
        return_air: List[Dict[str, Any]] = []
        equipment: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            air_supply.append({
                "id": f"AS-{rid}", "room_id": rid,
                "name": f"{name}送风口",
                "spec": {"type": "slot_diffuser", "airflow_cmh": 180},
            })
            return_air.append({
                "id": f"RA-{rid}", "room_id": rid,
                "name": f"{name}回风口",
                "spec": {"type": "grille", "airflow_cmh": 160},
            })
            constraints.append({
                "type": "noise", "room_id": rid,
                "description": f"{name}风口噪声不超过室内舒适限值（Mock 约束）",
            })
        equipment.append({
            "id": "AC-1", "name": "多联机室内机（Mock）",
            "spec": {"capacity_kw": 7.1,
                     "serves": [r.get("room_id") for r in
                                layout.get("rooms", []) or []]},
        })
        return HVACModel(air_supply=air_supply, return_air=return_air,
                         equipment=equipment, constraints=constraints)


__all__ = ["HVACRuleEngine"]
