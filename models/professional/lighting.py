"""models.professional.lighting · 照明深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class LightingModel(ProfessionalModel):
    discipline: str = "LIGHTING"
    fixtures: List[Dict[str, Any]] = field(default_factory=list)    # 灯具
    switches: List[Dict[str, Any]] = field(default_factory=list)    # 照明开关
    circuits: List[Dict[str, Any]] = field(default_factory=list)    # 照明回路
