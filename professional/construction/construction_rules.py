"""
InteriorDesignOS · ConstructionRuleEngine（Phase 5.1 §9，Mock Logic）

施工说明专业规则层：LayoutModel -> ConstructionModel（无 IO / 无副作用）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from professional.base.rule_engine import BaseRuleEngine
from professional.construction.construction_model import ConstructionModel


class ConstructionRuleEngine(BaseRuleEngine):
    """施工说明专业规则引擎（Mock）。"""

    discipline = "construction"

    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None
              ) -> ConstructionModel:
        notes: List[Dict[str, Any]] = []
        details: List[Dict[str, Any]] = []
        specifications: List[Dict[str, Any]] = []
        constraints: List[Dict[str, Any]] = []

        bearing_walls = [w for w in layout.get("walls", []) or []
                         if str(w.get("type", "")).upper() == "BEARING"]
        notes.append({
            "id": "N-1", "name": "承重墙保护说明",
            "spec": {"text": f"共 {len(bearing_walls)} 面承重墙，"
                             "严禁拆改（Mock 说明）"},
        })
        for room in layout.get("rooms", []) or []:
            rid = room.get("room_id", "R?")
            name = room.get("name", rid)
            details.append({
                "id": f"DT-{rid}", "room_id": rid,
                "name": f"{name}施工节点（Mock）",
                "spec": {"topic": "finish_junction"},
            })
        specifications.append({
            "id": "SP-1", "name": "通用施工规范引用",
            "spec": {"standard": "住宅装饰装修工程施工规范（Mock 引用）"},
        })
        constraints.append({
            "type": "safety",
            "description": "施工全程不得破坏承重结构与既有管井（Mock 约束）",
        })
        return ConstructionModel(notes=notes, details=details,
                                 specifications=specifications,
                                 constraints=constraints)


__all__ = ["ConstructionRuleEngine"]
