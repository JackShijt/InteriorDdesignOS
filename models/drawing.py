"""models.drawing · 施工图模型（Geometry → Drawing 产物）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base.model import Model


@dataclass
class DrawingModel(Model):
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    sheets: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    titleblock: Dict[str, Any] = field(default_factory=dict)
    coordinate_system: str = "mm"
    units: str = "mm"
