"""
InteriorDesignOS · Lighting Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → LightingAgent → LightingRuleEngine → LightingModel
Agent 只负责流程；专业规则在 LightingRuleEngine。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.lighting.lighting_rules import LightingRuleEngine


class LightingAgent(BaseProfessionalAgent):
    """照明专业深化 Agent（流程层）。"""

    discipline = "lighting"
    rule_engine_class = LightingRuleEngine


__all__ = ["LightingAgent"]
