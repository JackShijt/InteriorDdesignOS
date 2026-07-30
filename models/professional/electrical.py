"""models.professional.electrical · 电气深化模型（Phase 9 §1）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.professional.base import ProfessionalModel


@dataclass
class ElectricalModel(ProfessionalModel):
    discipline: str = "ELECTRICAL"
    circuits: List[Dict[str, Any]] = field(default_factory=list)   # 配电回路
    devices: List[Dict[str, Any]] = field(default_factory=list)    # 插座 / 开关
    panels: List[Dict[str, Any]] = field(default_factory=list)     # 配电箱
