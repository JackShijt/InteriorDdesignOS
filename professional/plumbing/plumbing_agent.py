"""
InteriorDesignOS · Plumbing Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → PlumbingAgent → PlumbingRuleEngine → PlumbingModel
Agent 只负责流程；专业规则在 PlumbingRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.plumbing.plumbing_rules import PlumbingRuleEngine


class PlumbingAgent(BaseProfessionalAgent):
    """给排水专业深化 Agent（流程层）。"""

    discipline = "plumbing"
    rule_engine_class = PlumbingRuleEngine


__all__ = ["PlumbingAgent"]
