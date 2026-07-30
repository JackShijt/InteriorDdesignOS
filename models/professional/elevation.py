"""models.professional.elevation · 立面深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class ElevationModel(ProfessionalModel):
    discipline: str = "ELEVATION"
    elevations: List[Dict[str, Any]] = field(default_factory=list)  # 立面
    elements: List[Dict[str, Any]] = field(default_factory=list)    # 立面构件
