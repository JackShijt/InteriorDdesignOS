"""models.professional.plumbing · 给排水深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class PlumbingModel(ProfessionalModel):
    discipline: str = "PLUMBING"
    supply_pipes: List[Dict[str, Any]] = field(default_factory=list)  # 给水管
    drain_pipes: List[Dict[str, Any]] = field(default_factory=list)  # 排水管
    fixtures: List[Dict[str, Any]] = field(default_factory=list)      # 卫生器具
    water_heaters: List[Dict[str, Any]] = field(default_factory=list)
