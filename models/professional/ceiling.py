"""models.professional.ceiling · 吊顶深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class CeilingModel(ProfessionalModel):
    discipline: str = "CEILING"
    planes: List[Dict[str, Any]] = field(default_factory=list)      # 吊顶平面
    beams: List[Dict[str, Any]] = field(default_factory=list)       # 梁
    openings: List[Dict[str, Any]] = field(default_factory=list)    # 吊顶开洞
