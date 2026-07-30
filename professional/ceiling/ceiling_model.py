"""CeilingModel（Phase 5 §5）：ceiling_regions / levels / materials。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class CeilingModel(BaseProfessionalModel):
    """吊顶专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "CEILING"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "ceiling_regions", "levels", "materials")

    ceiling_regions: List[Dict[str, Any]] = field(default_factory=list)
    levels: List[Dict[str, Any]] = field(default_factory=list)
    materials: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["CeilingModel"]
