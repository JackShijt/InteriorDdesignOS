"""
InteriorDesignOS · Furniture Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → FurnitureAgent → FurnitureRuleEngine → FurnitureModel
Agent 只负责流程；专业规则在 FurnitureRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.furniture.furniture_rules import FurnitureRuleEngine


class FurnitureAgent(BaseProfessionalAgent):
    """家具专业深化 Agent（流程层）。"""

    discipline = "furniture"
    rule_engine_class = FurnitureRuleEngine


__all__ = ["FurnitureAgent"]
