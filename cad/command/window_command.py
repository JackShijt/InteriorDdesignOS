"""WindowCommand（Phase 6 §4）— 窗领域命令。

以「沿洞口方向的双线」表示（两条偏移 draw_line）。
不直接调用 CAD，仅委托 CADAdapter。
"""
from __future__ import annotations

from typing import Any

from .drawing_command import COMMAND_REGISTRY, DrawingCommand


class WindowCommand(DrawingCommand):
    command_type = "window"

    def __init__(self, window_id: str, start: Any, end: Any, offset: float = 60,
                 layer: str = "WIN", **_kw):
        super().__init__({"window_id": window_id, "start": start, "end": end,
                          "offset": offset, "layer": layer})

    def execute(self, adapter: Any) -> Any:
        l1 = adapter.draw_line(self.params["start"], self.params["end"],
                               self.params["layer"])
        s2 = [self.params["start"][0], self.params["start"][1] + self.params["offset"]]
        e2 = [self.params["end"][0], self.params["end"][1] + self.params["offset"]]
        l2 = adapter.draw_line(s2, e2, self.params["layer"])
        return {"window_id": self.params["window_id"], "line_1": l1, "line_2": l2}


COMMAND_REGISTRY["window"] = WindowCommand

__all__ = ["WindowCommand"]
