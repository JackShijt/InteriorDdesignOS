"""models.design · 设计规格模型。"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base.model import Model


@dataclass
class DesignSpec(Model):
    requirements: List[Dict[str, Any]] = field(default_factory=list)
    style: str = "modern"
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
