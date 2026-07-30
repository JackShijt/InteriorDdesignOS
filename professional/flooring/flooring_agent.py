"""
InteriorDesignOS · Flooring Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → FlooringAgent → FlooringRuleEngine → FlooringModel
Agent 只负责流程；专业规则在 FlooringRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.flooring.flooring_rules import FlooringRuleEngine


class FlooringAgent(BaseProfessionalAgent):
    """地面专业深化 Agent（流程层）。"""

    discipline = "flooring"
    rule_engine_class = FlooringRuleEngine


__all__ = ["FlooringAgent"]
