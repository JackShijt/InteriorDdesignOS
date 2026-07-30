"""DoorCommand（Phase 6 §4）— 门领域命令。

以「门洞线 + 开启弧」表示：draw_line（门扇）+ draw_arc（开启轨迹）。
不直接调用 CAD，仅委托 CADAdapter。
"""
from __future__ import annotations

from typing import Any

from .drawing_command import COMMAND_REGISTRY, DrawingCommand


class DoorCommand(DrawingCommand):
    command_type = "door"

    def __init__(self, door_id: str, start: Any, end: Any, width: float = 900,
                 swing: float = 90, layer: str = "DOOR", **_kw):
        super().__init__({"door_id": door_id, "start": start, "end": end,
                          "width": width, "swing": swing, "layer": layer})

    def execute(self, adapter: Any) -> Any:
        leaf = adapter.draw_line(self.params["start"], self.params["end"],
                                 self.params["layer"])
        arc = adapter.draw_arc(self.params["start"], self.params["width"],
                               0.0, float(self.params["swing"]),
                               self.params["layer"])
        return {"door_id": self.params["door_id"], "leaf": leaf, "arc": arc}


COMMAND_REGISTRY["door"] = DoorCommand

__all__ = ["DoorCommand"]
