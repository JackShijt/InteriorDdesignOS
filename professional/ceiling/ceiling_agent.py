"""
InteriorDesignOS · Ceiling Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → CeilingAgent → CeilingRuleEngine → CeilingModel
Agent 只负责流程；专业规则在 CeilingRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.ceiling.ceiling_rules import CeilingRuleEngine


class CeilingAgent(BaseProfessionalAgent):
    """吊顶专业深化 Agent（流程层）。"""

    discipline = "ceiling"
    rule_engine_class = CeilingRuleEngine


__all__ = ["CeilingAgent"]
