"""Test 2（Phase 13 §11）：DrawingModel → Command List，检查命令类型映射。

WALL → CREATE_LINE；FURNITURE → CREATE_BLOCK；DIM → CREATE_DIMENSION。
"""

import json
from pathlib import Path

from mcp.cad_adapter.command_mapper import CommandMapper, validate_command

ROOT = Path(__file__).resolve().parents[2]
DRAWING = ROOT / "schemas" / "examples" / "DrawingModel.example.json"
GEOMETRY = ROOT / "schemas" / "examples" / "GeometryModel.example.json"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_drawing_wall_to_create_line():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    # WALL 实体为 E001-E004（geometry_ref L001/L002/L003/L007）
    wall_ids = {"E001", "E002", "E003", "E004"}
    wall_cmds = [c for c in commands
                 if c["payload"].get("entity_id") in wall_ids
                 and c["command_type"] == "CREATE_LINE"]
    assert len(wall_cmds) == 4
    for c in wall_cmds:
        assert c["command_type"] == "CREATE_LINE"
        assert c["payload"]["layer"] == "WALL"


def test_drawing_door_to_create_line():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    door = next(c for c in commands
                if c["payload"].get("entity_id") == "E006")
    assert door["command_type"] == "CREATE_LINE"


def test_drawing_furniture_to_create_block():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    block_cmds = [c for c in commands if c["command_type"] == "CREATE_BLOCK"]
    assert len(block_cmds) == 1
    assert block_cmds[0]["payload"]["entity_id"] == "E005"


def test_drawing_dimension_to_create_dimension():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    dim_cmds = [c for c in commands if c["command_type"] == "CREATE_DIMENSION"]
    assert len(dim_cmds) == 2
    for c in dim_cmds:
        assert c["payload"]["entity_id"] in ("DM001", "DM002")


def test_drawing_layers_and_annotations():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    assert sum(1 for c in commands if c["command_type"] == "CREATE_LAYER") == 4
    assert sum(1 for c in commands if c["command_type"] == "CREATE_TEXT") == 1


def test_drawing_commands_conform_to_contract():
    dm = _load(DRAWING)
    commands = CommandMapper().map_drawing_model(dm)
    for cmd in commands:
        validate_command(cmd)
        assert cmd["source_model"] == "DrawingModel"


def test_drawing_resolves_geometry_coordinates():
    dm = _load(DRAWING)
    gm = _load(GEOMETRY)
    commands = CommandMapper().map_drawing_model(dm, gm)
    # WALL E001 引用 L001 → 应解析出 start/end 坐标
    e001 = next(c for c in commands
                if c["payload"].get("entity_id") == "E001")
    assert e001["command_type"] == "CREATE_LINE"
    assert e001["payload"]["start"] == [0, 0]
    assert e001["payload"]["end"] == [6000, 0]
