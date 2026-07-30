"""Phase 6 §4 · DrawingCommand 命令模式测试。

验证：
- 各命令 execute 在 MockAdapter 上产生正确的 op 记录
- to_dict / from_dict 经 COMMAND_REGISTRY 可重建（回放）
- 未知 command_type 反序列化抛错
"""
from __future__ import annotations

from cad import MockAdapter
from cad.command.drawing_command import (COMMAND_REGISTRY, CreateLayerCommand,
                                         DrawLineCommand, DrawingCommandQueue)
from cad.command.wall_command import WallCommand
from cad.command.door_command import DoorCommand
from cad.command.window_command import WindowCommand
from cad.command.furniture_command import FurnitureCommand
from cad.command.dimension_command import DimensionCommand


def test_command_execute_produces_record():
    adapter = MockAdapter()
    adapter.connect()
    adapter.open_document("d.dwg")

    rec = CreateLayerCommand("WALL", 7, "Continuous").execute(adapter)
    assert rec["op"] == "create_layer" and rec["layer"] == "WALL"

    rec = DrawLineCommand([0, 0], [1000, 0], "WALL").execute(adapter)
    assert rec["op"] == "draw_line"

    rec = WallCommand("W1", [[0, 0], [1000, 0]], 100).execute(adapter)
    assert rec["op"] == "draw_polyline" and rec["width"] == 100

    rec = DoorCommand("D1", [0, 0], [900, 0]).execute(adapter)
    assert "leaf" in rec and "arc" in rec

    rec = WindowCommand("WIN1", [0, 0], [1000, 0]).execute(adapter)
    assert rec["line_1"] and rec["line_2"]

    rec = FurnitureCommand("F1", "SOFA", [100, 100]).execute(adapter)
    assert rec["op"] == "insert_block" and rec["block_ref"] == "SOFA"

    rec = DimensionCommand("DM1", [0, 0], [6000, 0], 6000).execute(adapter)
    assert rec["op"] == "create_dimension" and rec["value"] == 6000

    adapter.disconnect()


def test_command_roundtrip_via_registry():
    original = [
        CreateLayerCommand("WALL", 7, "Continuous"),
        WallCommand("W1", [[0, 0], [1000, 0]], 100),
        DoorCommand("D1", [0, 0], [900, 0]),
        WindowCommand("WIN1", [0, 0], [1000, 0]),
        FurnitureCommand("F1", "SOFA", [100, 100]),
        DimensionCommand("DM1", [0, 0], [6000, 0], 6000),
    ]
    queue = DrawingCommandQueue(original)
    serialized = queue.to_dict()
    restored = DrawingCommandQueue.from_dict(serialized)
    assert len(restored) == len(original)
    for a, b in zip(original, restored):
        assert type(a) is type(b)
        assert a.to_dict() == b.to_dict()


def test_unknown_command_type_raises():
    from cad.command.drawing_command import DrawingCommand
    import pytest
    with pytest.raises(ValueError):
        DrawingCommand.from_dict({"command_type": "nope", "params": {}})


def test_registry_contains_domain_commands():
    for t in ("wall", "door", "window", "furniture", "dimension",
              "create_layer", "draw_line", "draw_polyline", "draw_arc",
              "draw_circle", "insert_block", "create_text"):
        assert t in COMMAND_REGISTRY
