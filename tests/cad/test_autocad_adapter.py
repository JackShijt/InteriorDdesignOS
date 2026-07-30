"""Phase 7 §6 · AutoCAD Adapter 集成测试（Mock 模式，不连接真实 AutoCAD）。

通过注入 FakeMCPClient 验证真实执行通道（CADAdapter → MCPClient → AutoCAD MCP）：

- 连接 / 断开生命周期
- 命令执行：Line / Polyline / Text / Dimension 确实转译为 MCP 工具调用
- 错误处理：MCP 断开、命令失败、事务回滚
- 导出：经 MCP 请求导出，不直接生成 DWG
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cad import (AutoCADAdapter, CADSession, CreateLayerCommand,
                 CreateTextCommand, DimensionCommand, DrawLineCommand,
                 DrawPolylineCommand, DrawingCommandQueue)
from cad.mcp.mcp_exception import MCPConnectionError, MCPToolError


class FakeMCPClient:
    """成功模式 MCPClient：记录每次工具调用，不真正连接 AutoCAD。"""

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


class FailingMCPClient(FakeMCPClient):
    """在指定的工具名上抛 MCPToolError（模拟命令执行失败）。"""

    def __init__(self, fail_tool="cad.draw_polyline"):
        super().__init__()
        self.fail_tool = fail_tool

    def call_tool(self, name, arguments):
        if name == self.fail_tool:
            raise MCPToolError(f"工具 {name} 执行失败", tool=name)
        return super().call_tool(name, arguments)


class DisconnectingMCPClient(FakeMCPClient):
    """在指定的工具上模拟 MCP 已断开（抛 MCPConnectionError）；其余正常。"""

    def __init__(self, fail_tool="cad.draw_line"):
        super().__init__()
        self.fail_tool = fail_tool

    def call_tool(self, name, arguments):
        if name == self.fail_tool:
            raise MCPConnectionError(f"MCP 已断开，无法调用 {name}")
        return super().call_tool(name, arguments)


# ---- 连接 / 断开 ----
def test_connect_disconnect_lifecycle():
    adapter = AutoCADAdapter(client=FakeMCPClient())
    assert adapter.connected is False
    adapter.connect()
    assert adapter.connected is True
    adapter.disconnect()
    assert adapter.connected is False


# ---- 命令执行 ----
def test_line_polyline_text_dimension_execution():
    fake = FakeMCPClient()
    adapter = AutoCADAdapter(client=fake)

    adapter.connect()
    adapter.create_layer("WALL", 7, "Continuous")
    adapter.draw_line([0, 0], [1000, 0], "WALL")
    adapter.draw_polyline([[0, 0], [1000, 0], [1000, 1000]], "WALL")
    adapter.create_text("客厅", [100, 100], 300, "DIM")
    adapter.create_dimension([0, 0], [1000, 0], "DIM")
    adapter.disconnect()

    # 命令确实转译为 MCP 工具调用
    called = {c[0] for c in fake.calls}
    assert "cad.draw_line" in called
    assert "cad.draw_polyline" in called
    assert "cad.create_text" in called
    assert "cad.create_dimension" in called

    # 参数被正确转译（坐标序列化为 list）
    line_args = dict(fake.calls)["cad.draw_line"]
    assert line_args["start"] == [0, 0]
    assert line_args["end"] == [1000, 0]
    assert line_args["layer"] == "WALL"

    # 执行历史记录到 adapter.execution_log
    ops = {r["op"] for r in adapter.execution_log}
    assert {"create_layer", "draw_line", "draw_polyline",
            "create_text", "create_dimension"} <= ops


# ---- 错误处理：MCP 断开 ----
def test_mcp_disconnect_raises_in_session():
    adapter = AutoCADAdapter(client=DisconnectingMCPClient(fail_tool="cad.draw_line"))
    session = CADSession(adapter)
    session.open("P1")  # open_document 正常
    queue = DrawingCommandQueue()
    queue.append(CreateLayerCommand("WALL"))
    queue.append(DrawLineCommand([0, 0], [1, 1], "WALL"))  # 此处断开

    with pytest.raises(MCPConnectionError):
        session.run(queue)
    session.close()


# ---- 错误处理：命令失败 + 事务回滚 ----
def test_command_failure_triggers_rollback():
    adapter = AutoCADAdapter(client=FailingMCPClient())
    session = CADSession(adapter)
    session.open("P1")

    queue = DrawingCommandQueue()
    queue.append(CreateLayerCommand("WALL"))
    queue.append(DrawLineCommand([0, 0], [1, 1], "WALL"))
    queue.append(DrawPolylineCommand(  # 该工具会被 FailingMCPClient 拒绝
        [[0, 0], [1, 1]], "WALL"))

    # run(transactional=True) 内部 begin → 失败 → 自动 rollback
    with pytest.raises(MCPToolError):
        session.run(queue, transactional=True)

    # 事务回滚：当前事务清空，无已提交记录
    assert session.current_txn is None
    assert len(session.committed_records) == 0
    session.close()


def test_transaction_rollback_via_session_run():
    adapter = AutoCADAdapter(client=FailingMCPClient())
    session = CADSession(adapter)
    session.open("P1")

    queue = DrawingCommandQueue()
    queue.append(CreateLayerCommand("WALL"))
    queue.append(DrawPolylineCommand([[0, 0], [1, 1]], "WALL"))

    with pytest.raises(MCPToolError):
        session.run(queue, transactional=True)  # run 内部 begin → 失败 → rollback

    assert session.current_txn is None
    session.close()


# ---- 导出：经 MCP，不直接生成 DWG ----
def test_export_requests_via_mcp_not_local_dwg(tmp_path: Path):
    fake = FakeMCPClient()
    adapter = AutoCADAdapter(client=fake)
    adapter.connect()
    out = tmp_path / "plan.dwg"
    rec = adapter.export(out)

    # export 返回经 MCP 的调用记录，backend 标记为 autocad
    assert rec["op"] == "export"
    assert rec["backend"] == "autocad"
    assert ("cad.export", {"path": str(out)}) in fake.calls
    # 关键约束：绝不直接在本地写 DWG 文件
    assert not out.exists()
    adapter.disconnect()
