"""
InteriorDesignOS · ElectricalRuleEngine（Phase 5.1 §9，Mock Logic）

电气专业规则层：LayoutModel -> ElectricalModel。
Agent 负责流程；本引擎只负责专业规则（无 IO / 无日志 / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.electrical.electrical_model import ElectricalModel


class ElectricalRuleEngine(BaseRuleEngine):
    """电气专业规则引擎（Mock）。"""

    discipline = "electrical"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None) -> ElectricalModel:
        switches: List[Dict[str, Any]] = []
        sockets: List[Dict[str, Any]] = []
        lights: List[Dict[str, Any]] = []
        circuits: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            switches.append({
                "id": f"SW-{rid}", "room_id": rid,
                "name": f"{name}主开关",
                "spec": {"type": "single_pole", "gang": 1},
            })
            for i in range(1, 3):
                sockets.append({
                    "id": f"SK-{rid}-{i}", "room_id": rid,
                    "name": f"{name}插座{i}",
                    "spec": {"type": "5_hole", "rating": "10A"},
                })
            lights.append({
                "id": f"LT-{rid}", "room_id": rid,
                "name": f"{name}照明回路点位",
                "spec": {"type": "ceiling", "power_w": 24},
            })
            circuits.append({
                "id": f"C-{rid}", "room_id": rid,
                "name": f"{name}回路",
                "spec": {"breaker": "16A", "loads": [f"LT-{rid}", f"SK-{rid}-1",
                                                     f"SK-{rid}-2"]},
            })
            constraints.append({
                "type": "code", "room_id": rid,
                "description": f"{name}插座回路须配剩余电流保护（Mock 规范约束）",
            })

        panel = {
            "id": "PANEL-1",
            "name": "户内配电箱",
            "spec": {"main_breaker": "63A",
                     "circuit_count": len(circuits)},
        }
        return ElectricalModel(switches=switches, sockets=sockets,
                               lights=lights, circuits=circuits, panel=panel,
                               constraints=constraints)


__all__ = ["ElectricalRuleEngine"]
