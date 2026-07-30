"""MCPClient（Phase 7 §1）— 封装 MCP 通信。

职责（任务 §1）：
- ``connect`` / ``disconnect``：建立 / 释放与 MCP 服务的传输连接
- ``call_tool``：调用一个 MCP 工具（AutoCAD MCP 服务暴露的 ``cad.*`` 工具）
- ``send_command``：通用命令通道（如 AutoCAD 命令行）
- ``query_state``：查询 AutoCAD 当前文档 / 连接状态

约束（任务 §1）：
- 不知道 CAD 业务（只传 tool name + arguments，翻译在 AutoCADAdapter 完成）
- 不依赖 Agent / Runtime（仅标准库 + cad.mcp.protocol / cad.mcp.exception）
- 通过可注入的 ``transport`` 与具体 MCP 传输（stdio / http）解耦，
  便于测试（FakeTransport）与未来扩展，且不写死任何 CAD 软件 API
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .mcp_exception import MCPConnectionError, MCPError, MCPToolError
from .mcp_protocol import (MCP_METHOD_PING, MCP_METHOD_TOOLS_LIST,
                           make_request, make_tool_call, parse_response)


class MCPTransport(ABC):
    """MCP 传输抽象（stdio / http / 测试 Fake 均可实现）。"""

    @abstractmethod
    def connect(self) -> None:
        """建立传输层连接（如握手 / 打开管道）。"""

    @abstractmethod
    def disconnect(self) -> None:
        """释放传输层连接。"""

    @abstractmethod
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送一个 JSON-RPC 信封并返回解析后的响应 dict。"""


class HTTPMCPTransport(MCPTransport):
    """基于 HTTP 的 MCP 传输（JSON-RPC over HTTP POST）。

    仅依赖标准库 ``urllib``，不引入额外三方依赖；
    任何网络失败都转译为 ``MCPConnectionError``，由上层处理。
    """

    def __init__(self, host: str, port: int, timeout: float = 30,
                 path: str = "/mcp"):
        if not host:
            raise MCPConnectionError("HTTPMCPTransport 需要 host")
        self.base_url = f"http://{host}:{port}{path}"
        self.timeout = timeout
        self._connected = False

    def connect(self) -> None:
        # 通过 ping 验证可达性；失败即视为连接失败
        try:
            self.send(make_request(0, MCP_METHOD_PING))
            self._connected = True
        except MCPConnectionError:
            raise
        except Exception as e:  # noqa: BLE001 — 统一为连接错误
            raise MCPConnectionError(f"连接 AutoCAD MCP 失败：{e}")

    def disconnect(self) -> None:
        self._connected = False

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.error
        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url, data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise MCPConnectionError(f"MCP 传输失败：{e}")
        except Exception as e:  # noqa: BLE001
            raise MCPConnectionError(f"MCP 传输异常：{e}")


class MCPClient:
    """MCP 客户端：封装工具调用 / 命令发送 / 状态查询。

    不直接接触 CAD 业务；所有绘制语义由 AutoCADAdapter 翻译为工具名 + 参数。
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 timeout: float = 30, transport: Optional[MCPTransport] = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._transport = transport or self._build_transport()
        self._req_id = 0
        self.connected = False

    def _build_transport(self) -> Optional[MCPTransport]:
        if self.host:
            return HTTPMCPTransport(self.host, self.port or 0, self.timeout)
        return None  # 未配置 host → 需注入 transport 或在 connect 时报错

    # ---- 连接生命周期 ----
    def connect(self) -> None:
        if self._transport is None:
            raise MCPConnectionError(
                "未配置 MCP transport（需提供 host 或注入 transport）")
        self._transport.connect()
        self.connected = True

    def disconnect(self) -> None:
        if self._transport is not None:
            try:
                self._transport.disconnect()
            finally:
                self.connected = False

    # ---- 工具调用 ----
    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用一个 MCP 工具，返回解析后的业务结果。

        未连接 / 传输失败 / 工具错误均转译为 MCPError 向上抛出，
        交由 AutoCADAdapter → CADSession 触发事务回滚。
        """
        if self._transport is None:
            raise MCPConnectionError("MCP 未连接：缺少 transport")
        payload = make_tool_call(self._next_id(), name, arguments)
        try:
            resp = self._transport.send(payload)
        except MCPConnectionError:
            self.connected = False
            raise
        except Exception as e:  # noqa: BLE001
            self.connected = False
            raise MCPConnectionError(f"MCP 调用异常：{e}")
        return parse_response(resp)

    def send_command(self, command: str) -> Any:
        """通用命令通道（如 AutoCAD 命令行字符串）。"""
        from .mcp_protocol import TOOL_SEND_COMMAND
        return self.call_tool(TOOL_SEND_COMMAND, {"command": command})

    def query_state(self) -> Any:
        """查询 AutoCAD 当前文档 / 连接状态。"""
        from .mcp_protocol import TOOL_QUERY_STATE
        return self.call_tool(TOOL_QUERY_STATE, {})

    def list_tools(self) -> Any:
        """列出 MCP 服务暴露的工具。"""
        if self._transport is None:
            raise MCPConnectionError("MCP 未连接：缺少 transport")
        payload = make_request(self._next_id(), MCP_METHOD_TOOLS_LIST)
        try:
            resp = self._transport.send(payload)
        except MCPConnectionError:
            self.connected = False
            raise
        return parse_response(resp)


__all__ = ["MCPTransport", "HTTPMCPTransport", "MCPClient",
           "MCPConnectionError", "MCPToolError", "MCPError"]
