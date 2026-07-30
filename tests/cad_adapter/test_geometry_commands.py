"""Test 1（Phase 13 §11）：GeometryModel → CAD Commands，数量一致。

验证 command_mapper 能将 GeometryModel 的几何基元一对一翻译为 CAD Command，
且命令符合 CAD Tool Command Contract。
"""

import json
from pathlib import Path

from mcp.cad_adapter.command_mapper import CommandMapper, validate_command

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "examples" / "GeometryModel.example.json"


def _load():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_geometry_to_commands_count_consistent():
    gm = _load()
    commands = CommandMapper().map_geometry_model(gm)

    n_lines = len(gm.get("lines", []))
    n_polys = len(gm.get("polygons", []))
    n_dims = len(gm.get("dimensions", []))

    # 数量一致：每条几何基元 → 一条 CAD Command
    assert len(commands) == n_lines + n_polys + n_dims
    assert len(commands) == 8 + 5 + 3
    assert len(commands) == 16


def test_geometry_command_types():
    gm = _load()
    commands = CommandMapper().map_geometry_model(gm)

    types = [c["command_type"] for c in commands]
    assert types.count("CREATE_LINE") == 8
    assert types.count("CREATE_POLYLINE") == 5
    assert types.count("CREATE_DIMENSION") == 3


def test_geometry_commands_conform_to_contract():
    gm = _load()
    commands = CommandMapper().map_geometry_model(gm)
    for cmd in commands:
        validate_command(cmd)  # 不抛异常即通过
        assert cmd["source_model"] == "GeometryModel"
        assert cmd["payload"]["geometry_ref"]


def test_geometry_line_carries_coordinates():
    gm = _load()
    commands = CommandMapper().map_geometry_model(gm)
    line_cmds = [c for c in commands if c["command_type"] == "CREATE_LINE"]
    # CREATE_LINE 至少一条带 start/end
    assert any(c["payload"].get("start") and c["payload"].get("end")
               for c in line_cmds)
