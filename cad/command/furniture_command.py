"""FurnitureCommand（Phase 6 §4）— 家具领域命令。

以「插入块」表示（insert_block）。
不直接调用 CAD，仅委托 CADAdapter。
"""
from __future__ import annotations

from typing import Any

from .drawing_command import COMMAND_REGISTRY, DrawingCommand


class FurnitureCommand(DrawingCommand):
    command_type = "furniture"

    def __init__(self, furniture_id: str, block_ref: str, position: Any,
                 scale: float = 1.0, rotation: float = 0.0,
                 layer: str = "FURN", **_kw):
        super().__init__({"furniture_id": furniture_id, "block_ref": block_ref,
                          "position": position, "scale": scale,
                          "rotation": rotation, "layer": layer})

    def execute(self, adapter: Any) -> Any:
        return adapter.insert_block(self.params["block_ref"],
                                    self.params["position"],
                                    self.params["scale"],
                                    self.params["rotation"],
                                    self.params["layer"])


COMMAND_REGISTRY["furniture"] = FurnitureCommand

__all__ = ["FurnitureCommand"]
