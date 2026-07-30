"""models.professional.construction · 施工深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class ConstructionModel(ProfessionalModel):
    discipline: str = "CONSTRUCTION"
    items: List[Dict[str, Any]] = field(default_factory=list)       # 施工项
    finishes: List[Dict[str, Any]] = field(default_factory=list)    # 饰面做法
