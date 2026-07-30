"""
InteriorDesignOS · Electrical Agent（Phase 5 §6 / Phase 5.1 重构）

LayoutModel → ElectricalAgent → ElectricalRuleEngine → ElectricalModel
Agent 只负责流程（validate / generate / publish）；
专业规则全部在 ElectricalRuleEngine（Phase 5.1 §9）。
"""
from __future__ import annotations

from professional.base.professional_agent import BaseProfessionalAgent
from professional.electrical.electrical_rules import ElectricalRuleEngine


class ElectricalAgent(BaseProfessionalAgent):
    """电气专业深化 Agent（流程层）。"""

    discipline = "electrical"
    rule_engine_class = ElectricalRuleEngine


__all__ = ["ElectricalAgent"]
