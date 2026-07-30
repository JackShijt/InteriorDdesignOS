"""FurnitureModel（Phase 5 §5）：movable / fixed / clearance。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class FurnitureModel(BaseProfessionalModel):
    """家具专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "FURNITURE"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "movable", "fixed", "clearance")

    movable: List[Dict[str, Any]] = field(default_factory=list)
    fixed: List[Dict[str, Any]] = field(default_factory=list)
    clearance: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["FurnitureModel"]
