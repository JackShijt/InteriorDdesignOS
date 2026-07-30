"""DimensionCommand（Phase 6 §4）— 尺寸标注领域命令。

委托 CADAdapter.create_dimension。
不直接调用 CAD。
"""
from __future__ import annotations

from typing import Any

from .drawing_command import COMMAND_REGISTRY, DrawingCommand


class DimensionCommand(DrawingCommand):
    command_type = "dimension"

    def __init__(self, dimension_id: str, start: Any, end: Any,
                 value: float | None = None, unit: str = "mm",
                 layer: str = "DIM", **_kw):
        super().__init__({"dimension_id": dimension_id, "start": start,
                          "end": end, "value": value, "unit": unit,
                          "layer": layer})

    def execute(self, adapter: Any) -> Any:
        return adapter.create_dimension(self.params["start"],
                                        self.params["end"],
                                        self.params["value"],
                                        self.params["unit"],
                                        self.params["layer"])


COMMAND_REGISTRY["dimension"] = DimensionCommand

__all__ = ["DimensionCommand"]
