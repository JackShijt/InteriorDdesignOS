"""WallCommand（Phase 6 §4）— 墙体领域命令。

墙体以「带宽度多段线」表示（polyline + width=thickness）。
不直接调用 CAD，仅委托 CADAdapter.draw_polyline。
"""
from __future__ import annotations

from typing import Any

from .drawing_command import COMMAND_REGISTRY, DrawingCommand


class WallCommand(DrawingCommand):
    command_type = "wall"

    def __init__(self, wall_id: str, points: Any, thickness: float = 100,
                 layer: str = "WALL", **_kw):
        super().__init__({"wall_id": wall_id, "points": points,
                          "thickness": thickness, "layer": layer})

    def execute(self, adapter: Any) -> Any:
        return adapter.draw_polyline(
            self.params["points"], self.params["layer"],
            width=self.params["thickness"], closed=False)


COMMAND_REGISTRY["wall"] = WallCommand

__all__ = ["WallCommand"]
