"""cad.mcp.autocad_mcp_client · AutoCAD MCP 客户端接口预留（Phase 12.3）。

要求（本阶段）：
- 提供 connect() / send_command() / execute() / query() / disconnect() 五个接口。
- **不要求真实连接**：未注入 transport 时，connect() 抛出
  ``MCPConnectionError``，由 AutoCADAdapter/capability 系统触发降级到 mock。
- 复用 Phase 7 的 ``MCPClient``（JSON-RPC 传输封装），本类只做
  AutoCAD 语义层的薄包装，不写死任何 AutoCAD API。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .mcp_client import MCPClient, MCPTransport
from .mcp_exception import MCPConnectionError


class AutoCADMCPClient:
    """AutoCAD MCP 客户端（接口预留，Phase 12.3）。

    用法（未来接真实 MCP 服务时）：
        client = AutoCADMCPClient(host="127.0.0.1", port=5001)
        client.connect()
        client.execute("cad.create_line", {...})
        client.disconnect()
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 timeout: float = 30,
                 transport: Optional[MCPTransport] = None):
        self._client = MCPClient(host=host, port=port, timeout=timeout,
                                 transport=transport)

    # ---- 连接生命周期 ---------------------------------------------------
    def connect(self) -> None:
        """建立与 AutoCAD MCP 服务的连接。

        本阶段无真实服务；未配置 host/transport 时抛 MCPConnectionError。
        """
        self._client.connect()

    def disconnect(self) -> None:
        """断开连接（幂等）。"""
        self._client.disconnect()

    @property
    def connected(self) -> bool:
        return self._client.connected

    # ---- 命令 / 工具通道 -------------------------------------------------
    def send_command(self, command: str) -> Any:
        """发送 AutoCAD 命令行字符串（如 "LINE 0,0 100,0"）。"""
        self._ensure_connected()
        return self._client.send_command(command)

    def execute(self, tool: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """执行一个 MCP 工具（AutoCAD MCP 服务暴露的 ``cad.*`` 工具）。"""
        self._ensure_connected()
        return self._client.call_tool(tool, arguments or {})

    def query(self, what: str = "state",
              arguments: Optional[Dict[str, Any]] = None) -> Any:
        """查询 AutoCAD 状态 / 文档信息。

        what="state" 走标准状态查询；其余走 ``cad.query.<what>`` 工具。
        """
        self._ensure_connected()
        if what == "state":
            return self._client.query_state()
        return self._client.call_tool(f"cad.query.{what}", arguments or {})

    # ---- 内部 -----------------------------------------------------------
    def _ensure_connected(self) -> None:
        if not self._client.connected:
            raise MCPConnectionError("AutoCAD MCP 未连接：请先 connect()")


__all__ = ["AutoCADMCPClient"]
