"""
InteriorDesignOS · BaseRuleEngine（Phase 5.1 §9）

职责分离：

    ProfessionalAgent   —— 负责流程（validate / generate / publish）
        |
    RuleEngine          —— 负责专业规则（本模块）
        |
    ProfessionalModel   —— 强类型 dataclass 结果

RuleEngine 约束：
- 纯函数式：输入 layout / design_spec（只读 dict），输出 ProfessionalModel
- 禁止 IO（不读写文件、不打日志、不触碰 Workspace）
- 禁止依赖 runtime / orchestrator / professional_agent
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from professional.base.professional_model import BaseProfessionalModel


class BaseRuleEngine(ABC):
    """专业规则引擎基类：layout(+design_spec) -> ProfessionalModel。"""

    #: 对应专业名（与 Agent.discipline 一致），子类声明
    discipline: str = "base"

    @abstractmethod
    def build(self, layout: Dict[str, Any],
              design_spec: Optional[Dict[str, Any]] = None
              ) -> BaseProfessionalModel:
        """应用专业规则，生成本专业的 ProfessionalModel。"""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # 公共只读工具（所有 RuleEngine 共享，DRY）
    # ------------------------------------------------------------------ #
    @staticmethod
    def rooms_of(layout: Dict[str, Any]) -> List[Dict[str, Any]]:
        return layout.get("rooms", []) or []

    @staticmethod
    def room_area(room: Dict[str, Any]) -> float:
        try:
            return float(room.get("area", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def room_type(room: Dict[str, Any]) -> str:
        return str(room.get("type") or room.get("room_type") or "").upper()

    @staticmethod
    def room_id(room: Dict[str, Any]) -> str:
        return str(room.get("id") or room.get("room_id") or "")

    @staticmethod
    def room_center(room: Dict[str, Any]) -> List[float]:
        c = room.get("center")
        if isinstance(c, (list, tuple)) and len(c) >= 2:
            return [float(c[0]), float(c[1])]
        bbox = room.get("bbox") or room.get("bounding_box")
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            return [(float(bbox[0]) + float(bbox[2])) / 2.0,
                    (float(bbox[1]) + float(bbox[3])) / 2.0]
        return [0.0, 0.0]


__all__ = ["BaseRuleEngine"]
