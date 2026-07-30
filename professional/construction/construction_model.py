"""ConstructionModel（Phase 5 §5）：notes / details / specifications。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class ConstructionModel(BaseProfessionalModel):
    """施工说明专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "CONSTRUCTION"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "notes", "details", "specifications")

    notes: List[Dict[str, Any]] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)
    specifications: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["ConstructionModel"]
