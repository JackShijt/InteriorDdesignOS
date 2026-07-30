"""FlooringModel（Phase 5 §5）：areas / materials / patterns。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class FlooringModel(BaseProfessionalModel):
    """地面专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "FLOORING"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "areas", "materials", "patterns")

    areas: List[Dict[str, Any]] = field(default_factory=list)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["FlooringModel"]
