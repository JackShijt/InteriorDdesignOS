"""LightingModel（Phase 5 §5）：fixtures / groups / controls。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class LightingModel(BaseProfessionalModel):
    """照明专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "LIGHTING"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "fixtures", "groups", "controls")

    fixtures: List[Dict[str, Any]] = field(default_factory=list)
    groups: List[Dict[str, Any]] = field(default_factory=list)
    controls: List[Dict[str, Any]] = field(default_factory=list)


__all__ = ["LightingModel"]
