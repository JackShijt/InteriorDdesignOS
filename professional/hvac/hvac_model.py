"""HVACModel（Phase 5 §5）：air_supply / return_air / equipment。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class HVACModel(BaseProfessionalModel):
    """暖通专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "HVAC"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "air_supply", "return_air", "equipment")

    air_supply: List[Dict[str, Any]] = field(default_factory=list)
    return_air: List[Dict[str, Any]] = field(default_factory=list)
    equipment: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["HVACModel"]
