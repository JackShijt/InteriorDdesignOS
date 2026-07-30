"""DrawingCommand（Phase 6 §4）— 命令模式基类 + 通用图元命令 + 命令队列。

命令模式：DrawingAgent 不直接调用 CAD，而是构造 DrawingCommand，
交由 CADSession + CADAdapter 执行（Phase 6 §4/§6）。

- DrawingCommand：抽象基类（execute(adapter) 由子类实现）
- 通用图元命令：CreateLayer / DrawLine / DrawPolyline / DrawArc /
  DrawCircle / InsertBlock / CreateText（一一映射 CADAdapter 接口）
- DrawingCommandQueue：有序命令集合（构建 / 序列化 / 反序列化）
- COMMAND_REGISTRY：command_type → 类，支撑 from_dict 重建（回放 / 测试）

依赖规则：禁止 import runtime / orchestrator / agents / professional。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type


class DrawingCommand(ABC):
    """命令抽象基类。"""

    command_type: str = "command"

    def __init__(self, params: Dict[str, Any] | None = None):
        self.params: Dict[str, Any] = dict(params or {})

    @abstractmethod
    def execute(self, adapter: Any) -> Dict[str, Any]:
        """在给定 CADAdapter 上执行，返回执行记录 dict。"""

    def to_dict(self) -> Dict[str, Any]:
        return {"command_type": self.command_type, "params": self.params}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrawingCommand":
        ctype = data.get("command_type")
        klass = COMMAND_REGISTRY.get(ctype)
        if klass is None:
            raise ValueError(f"未知 command_type: {ctype}")
        return klass(**data.get("params", {}))


# --------------------------------------------------------------------------- #
# 通用图元命令（与 CADAdapter 接口一一对应）
# --------------------------------------------------------------------------- #
class CreateLayerCommand(DrawingCommand):
    command_type = "create_layer"

    def __init__(self, layer: str, color: int = 7,
                 line_type: str = "Continuous", **_kw):
        super().__init__({"layer": layer, "color": color,
                          "line_type": line_type})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.create_layer(self.params["layer"],
                                    self.params["color"],
                                    self.params["line_type"])


class DrawLineCommand(DrawingCommand):
    command_type = "draw_line"

    def __init__(self, start: Any, end: Any, layer: str | None = None, **_kw):
        super().__init__({"start": start, "end": end, "layer": layer})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.draw_line(self.params["start"],
                                 self.params["end"],
                                 self.params["layer"])


class DrawPolylineCommand(DrawingCommand):
    command_type = "draw_polyline"

    def __init__(self, points: Any, layer: str | None = None,
                 width: float | None = None, closed: bool = False, **_kw):
        super().__init__({"points": points, "layer": layer,
                          "width": width, "closed": closed})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.draw_polyline(self.params["points"],
                                     self.params["layer"],
                                     self.params["width"],
                                     self.params["closed"])


class DrawArcCommand(DrawingCommand):
    command_type = "draw_arc"

    def __init__(self, center: Any, radius: float, start_angle: float,
                 end_angle: float, layer: str | None = None, **_kw):
        super().__init__({"center": center, "radius": radius,
                          "start_angle": start_angle, "end_angle": end_angle,
                          "layer": layer})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.draw_arc(self.params["center"], self.params["radius"],
                                self.params["start_angle"],
                                self.params["end_angle"],
                                self.params["layer"])


class DrawCircleCommand(DrawingCommand):
    command_type = "draw_circle"

    def __init__(self, center: Any, radius: float,
                 layer: str | None = None, **_kw):
        super().__init__({"center": center, "radius": radius, "layer": layer})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.draw_circle(self.params["center"],
                                  self.params["radius"],
                                  self.params["layer"])


class InsertBlockCommand(DrawingCommand):
    command_type = "insert_block"

    def __init__(self, block_ref: str, position: Any, scale: float = 1.0,
                 rotation: float = 0.0, layer: str | None = None, **_kw):
        super().__init__({"block_ref": block_ref, "position": position,
                          "scale": scale, "rotation": rotation,
                          "layer": layer})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.insert_block(self.params["block_ref"],
                                    self.params["position"],
                                    self.params["scale"],
                                    self.params["rotation"],
                                    self.params["layer"])


class CreateTextCommand(DrawingCommand):
    command_type = "create_text"

    def __init__(self, text: str, position: Any, height: float = 300,
                 layer: str | None = None, **_kw):
        super().__init__({"text": text, "position": position,
                          "height": height, "layer": layer})

    def execute(self, adapter: Any) -> Dict[str, Any]:
        return adapter.create_text(self.params["text"],
                                   self.params["position"],
                                   self.params["height"],
                                   self.params["layer"])


# --------------------------------------------------------------------------- #
# 命令队列
# --------------------------------------------------------------------------- #
class DrawingCommandQueue:
    """有序 DrawingCommand 集合。"""

    def __init__(self, commands: List[DrawingCommand] | None = None):
        self.commands: List[DrawingCommand] = list(commands or [])

    def append(self, command: DrawingCommand) -> None:
        self.commands.append(command)

    def extend(self, commands: List[DrawingCommand]) -> None:
        self.commands.extend(commands)

    def __len__(self) -> int:
        return len(self.commands)

    def __iter__(self):
        return iter(self.commands)

    def __getitem__(self, idx: int) -> DrawingCommand:
        return self.commands[idx]

    def to_dict(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.commands]

    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> "DrawingCommandQueue":
        return cls([DrawingCommand.from_dict(d) for d in data])


# 命令注册表（由本模块通用命令 + 各领域命令文件注入）
COMMAND_REGISTRY: Dict[str, Type[DrawingCommand]] = {
    "create_layer": CreateLayerCommand,
    "draw_line": DrawLineCommand,
    "draw_polyline": DrawPolylineCommand,
    "draw_arc": DrawArcCommand,
    "draw_circle": DrawCircleCommand,
    "insert_block": InsertBlockCommand,
    "create_text": CreateTextCommand,
}


__all__ = [
    "DrawingCommand", "DrawingCommandQueue", "COMMAND_REGISTRY",
    "CreateLayerCommand", "DrawLineCommand", "DrawPolylineCommand",
    "DrawArcCommand", "DrawCircleCommand", "InsertBlockCommand",
    "CreateTextCommand",
]
