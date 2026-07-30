"""ElectricalModel（Phase 5 §5）：switches / sockets / lights / circuits / panel。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Tuple

from professional.base.professional_model import BaseProfessionalModel


@dataclass
class ElectricalModel(BaseProfessionalModel):
    """电气专业模型（Mock 阶段）。"""

    DISCIPLINE: ClassVar[str] = "ELECTRICAL"
    COLLECTION_FIELDS: ClassVar[Tuple[str, ...]] = (
        "switches", "sockets", "lights", "circuits")
    SINGLE_FIELDS: ClassVar[Tuple[str, ...]] = ("panel",)

    switches: List[Dict[str, Any]] = field(default_factory=list)
    sockets: List[Dict[str, Any]] = field(default_factory=list)
    lights: List[Dict[str, Any]] = field(default_factory=list)
    circuits: List[Dict[str, Any]] = field(default_factory=list)
    panel: Dict[str, Any] = field(default_factory=dict)


__all__ = ["ElectricalModel"]
