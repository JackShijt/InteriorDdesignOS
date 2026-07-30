"""PlumbingModel（Phase 5 §5）：water_supply / drain / equipment。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class PlumbingModel(BaseProfessionalModel):
    """给排水专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "PLUMBING"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "water_supply", "drain", "equipment")

    water_supply: List[Dict[str, Any]] = field(default_factory=list)
    drain: List[Dict[str, Any]] = field(default_factory=list)
    equipment: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["PlumbingModel"]
