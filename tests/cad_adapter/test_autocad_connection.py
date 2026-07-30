"""Test 3（Phase 13 §11）：Adapter → MCP → AutoCAD 连接与测试线闭环验证。

说明：本环境未运行真实 AutoCAD / puran-water/autocad-mcp，故：
- 真实连接（默认 StdioMCPTransport）应判定为不可用（honest，不臆造）。
- 可验证闭环通过注入 SimulatedTransport（参考实现，非真实 MCP 源码）证明
  Adapter → MCP → AutoCAD → DWG 通路，并验证最终 DWG 文件存在。
"""

import json
from pathlib import Path

import pytest

from mcp.autocad.autocad_mcp_client import (
    AutoCADMCPClient,
    SimulatedTransport,
)
from mcp.cad_adapter import CADAdapter
from mcp.cad_adapter.command_mapper import CommandMapper, make_command  # noqa: F401
from mcp.cad_adapter.exceptions import AutoCADConnectionError

ROOT = Path(__file__).resolve().parents[2]
DRAWING = ROOT / "schemas" / "examples" / "DrawingModel.example.json"
GEOMETRY = ROOT / "schemas" / "examples" / "GeometryModel.example.json"


def test_real_connection_unavailable_offline():
    """真实 AutoCAD MCP 未配置时，连接不可用（诚实判定，不静默 fallback）。"""
    client = AutoCADMCPClient()  # 默认 StdioMCPTransport
    assert client.health_check() is False
    with pytest.raises(AutoCADConnectionError):
        client.connect()


def test_adapter_sends_test_line_and_dwg_exists(tmp_path):
    """Adapter → MCP → AutoCAD：创建一条测试线，验证 DWG 存在。"""
    dwg = tmp_path / "test_line.dwg"
    client = AutoCADMCPClient(transport=SimulatedTransport())
    adapter = CADAdapter(client)

    mapper = CommandMapper(id_prefix="T")
    commands = [
        make_command(
            "CREATE_LINE",
            {"entity_id": "E001", "layer": "WALL", "start": [0, 0], "end": [1000, 0]},
            "DrawingModel", "1.0", command_id="T-0001"),
        make_command(
            "SAVE_DWG", {"path": str(dwg)}, "DrawingModel", "1.0",
            command_id="T-0002"),
    ]

    report = adapter.run(commands, str(dwg))

    # DWG 存在
    assert dwg.exists(), "DWG 文件应被 AutoCAD MCP（SimulatedTransport）写出"
    # 测试线已执行并回写 handle
    assert report["entity_mapping_size"] == 1
    assert report["entity_mapping"]["E001"]["handle"]
    assert report["generated_model"]["counts"]["line"] == 1
    assert report["generated_model"]["counts"]["total"] == 1


def test_adapter_full_loop_drawing_model(tmp_path):
    """端到端：DrawingModel + GeometryModel → DWG → GeneratedModel。"""
    dwg = tmp_path / "demo.dwg"
    dm = json.loads(DRAWING.read_text(encoding="utf-8"))
    gm = json.loads(GEOMETRY.read_text(encoding="utf-8"))

    client = AutoCADMCPClient(transport=SimulatedTransport())
    adapter = CADAdapter(client)

    report = adapter.execute(dm, str(dwg), geometry_model=gm, project_id="Project_001")

    assert dwg.exists()
    gen = report["generated_model"]
    # 4 WALL + 1 DOOR = 5 线；1 FURNITURE 块；2 标注；4 图层；1 文字
    assert gen["counts"]["line"] == 5
    assert gen["counts"]["block"] == 1
    assert gen["counts"]["dimension"] == 2
    assert gen["counts"]["layer"] == 4
    assert gen["counts"]["text"] == 1
    assert gen["project_id"] == "Project_001"
    # entity 追踪：WALL E001 有 handle
    assert report["entity_mapping"]["E001"]["handle"]
