"""CADDocument（Phase 6 §3）— 打开的图纸文档抽象。

承载图层级与图元记录的轻量容器；具体后端可子类化以附加内存态。
依赖规则：禁止 import runtime / orchestrator / agents / professional。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class CADDocument:
    """打开的 CAD 文档（抽象）。

    - layers：图层名 → {color, line_type}
    - entities：按执行顺序累积的图元记录
    """

    def __init__(self, name: str, adapter: Any = None):
        self.name = name
        self.adapter = adapter
        self.layers: Dict[str, Dict[str, Any]] = {}
        self.entities: List[Dict[str, Any]] = []
        self.is_open = False

    def add_layer(self, name: str, color: int, line_type: str) -> None:
        self.layers[name] = {"color": color, "line_type": line_type}

    def add_entity(self, record: Dict[str, Any]) -> None:
        self.entities.append(record)

    def layer_count(self) -> int:
        return len(self.layers)

    def entity_count(self) -> int:
        return len(self.entities)

    def summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layers": list(self.layers),
            "entity_count": len(self.entities),
        }


__all__ = ["CADDocument"]
