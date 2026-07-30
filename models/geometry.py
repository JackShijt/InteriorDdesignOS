"""models.geometry · 几何模型（Layout → Geometry 产物）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base.model import Model


@dataclass
class GeometryModel(Model):
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    walls: List[Dict[str, Any]] = field(default_factory=list)
    furniture: List[Dict[str, Any]] = field(default_factory=list)
    doors: List[Dict[str, Any]] = field(default_factory=list)
    windows: List[Dict[str, Any]] = field(default_factory=list)
    coordinate_system: str = "mm"
    units: str = "mm"
    dimensions: List[Dict[str, Any]] = field(default_factory=list)
