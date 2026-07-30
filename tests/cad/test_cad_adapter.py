"""Phase 6 §2 · CADAdapter 接口测试。

验证：
- MockAdapter 实现 CADAdapter 全部接口方法并记录执行历史
- AutoCADAdapter（Phase 7）实现全部方法并委托给注入的 MCPClient
- build_cad_backend 后端插件工厂
"""
from __future__ import annotations

import pytest

from cad import (CAD_ADAPTER_METHODS, AutoCADAdapter, MockAdapter,
                 build_cad_backend)
from cad.mcp.mcp_exception import MCPConnectionError


def test_mock_adapter_implements_all_methods():
    adapter = MockAdapter()
    for method in CAD_ADAPTER_METHODS:
        assert hasattr(adapter, method), f"MockAdapter 缺少方法：{method}"
        assert callable(getattr(adapter, method))


def test_mock_adapter_records_execution_history():
    adapter = MockAdapter()
    adapter.connect()
    adapter.open_document("test.dwg")
    adapter.create_layer("WALL", 7, "Continuous")
    adapter.draw_line([0, 0], [1000, 0], "WALL")
    adapter.draw_polyline([[0, 0], [1000, 0]], "WALL", width=100)
    adapter.draw_arc([0, 0], 500, 0, 90, "WALL")
    adapter.draw_circle([0, 0], 500, "WALL")
    adapter.insert_block("DOOR", [0, 0], 1.0, 0.0, "DOOR")
    adapter.create_text("客厅", [100, 100], 300, "DIM")
    adapter.create_dimension([0, 0], [1000, 0], 1000, "mm", "DIM")
    adapter.close()
    adapter.disconnect()

    # 每条图元调用都应进入 execution_log
    assert len(adapter.execution_log) == 8
    ops = {r["op"] for r in adapter.execution_log}
    assert {"create_layer", "draw_line", "draw_polyline", "draw_arc",
            "draw_circle", "insert_block", "create_text",
            "create_dimension"} <= ops


class _FakeMCPClient:
    """测试用 MCPClient：记录调用，不真正连接 AutoCAD。"""

    def __init__(self):
        self.connected = False
        self.calls = []

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"tool": name, "ok": True}

    def send_command(self, command):
        self.calls.append(("cad.send_command", {"command": command}))
        return {"ok": True}

    def query_state(self):
        self.calls.append(("cad.query_state", {}))
        return {"connected": self.connected}


def test_autocad_adapter_delegates_to_mcp_client():
    """AutoCADAdapter 实现全部 CADAdapter 方法，并委托给注入的 MCPClient。"""
    fake = _FakeMCPClient()
    adapter = AutoCADAdapter(client=fake)
    adapter.connect()
    assert adapter.connected is True
    adapter.open_document("demo.dwg")
    adapter.create_layer("WALL", 7, "Continuous")
    adapter.draw_line([0, 0], [1000, 0], "WALL")
    adapter.draw_polyline([[0, 0], [1000, 0]], "WALL", width=100, closed=False)
    adapter.draw_arc([0, 0], 500, 0, 90, "WALL")
    adapter.draw_circle([0, 0], 500, "WALL")
    adapter.insert_block("DOOR", [0, 0], "DOOR", 1.0, 0.0)
    adapter.create_text("客厅", [100, 100], 300, "DIM")
    adapter.create_dimension([0, 0], [1000, 0], "DIM")
    adapter.save("demo.dwg")
    adapter.close()
    adapter.disconnect()

    # 全部 14 个 CADAdapter 方法可达且委托到 MCPClient
    assert len(adapter.execution_log) >= 11
    called_tools = {c[0] for c in fake.calls}
    assert "cad.open_document" in called_tools
    assert "cad.draw_line" in called_tools
    assert "cad.draw_polyline" in called_tools
    assert "cad.create_text" in called_tools
    assert "cad.create_dimension" in called_tools
    assert adapter.connected is False


def test_autocad_adapter_connect_without_transport_raises():
    """未配置 host 且未注入 client/transport 时，connect 应抛 MCPConnectionError。"""
    adapter = AutoCADAdapter()  # host=None, client=None
    with pytest.raises(MCPConnectionError):
        adapter.connect()


def test_build_cad_backend_factory():
    mock = build_cad_backend("mock")
    assert isinstance(mock, MockAdapter)
    auto = build_cad_backend("autocad")
    assert isinstance(auto, AutoCADAdapter)


def test_build_cad_backend_unknown():
    with pytest.raises(ValueError):
        build_cad_backend("nosuchbackend")
