"""
InteriorDesignOS · HVAC Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → HVACAgent → HVACRuleEngine → HVACModel
Agent 只负责流程；专业规则在 HVACRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.hvac.hvac_rules import HVACRuleEngine


class HVACAgent(BaseProfessionalAgent):
    """暖通专业深化 Agent（流程层）。"""

    discipline = "hvac"
    rule_engine_class = HVACRuleEngine


__all__ = ["HVACAgent"]
