"""models.layout · 平面布置模型（流水线输入）。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base.model import Model


@dataclass
class LayoutModel(Model):
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    furniture: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    walls: List[Dict[str, Any]] = field(default_factory=list)
    doors: List[Dict[str, Any]] = field(default_factory=list)
    windows: List[Dict[str, Any]] = field(default_factory=list)
