"""
InteriorDesignOS · Construction Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → ConstructionAgent → ConstructionRuleEngine → ConstructionModel
Agent 只负责流程；专业规则在 ConstructionRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.construction.construction_rules import ConstructionRuleEngine


class ConstructionAgent(BaseProfessionalAgent):
    """施工说明专业深化 Agent（流程层）。"""

    discipline = "construction"
    rule_engine_class = ConstructionRuleEngine


__all__ = ["ConstructionAgent"]
