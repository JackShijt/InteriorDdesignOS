"""MCP 异常（Phase 7 §1）。

MCP Client Layer 的异常层次；CAD 业务无关，仅表达通信 / 工具调用失败。
"""
from __future__ import annotations

from typing import Any, Optional


class MCPError(Exception):
    """MCP 通信基础异常。"""


class MCPConnectionError(MCPError):
    """连接 / 断开 MCP 失败（传输层）。

    例如未配置 host、网络不可达、握手（ping）失败。
    """


class MCPToolError(MCPError):
    """MCP 工具调用返回错误（应用层）。

    AutoCADAdapter 调用 ``cad.draw_line`` 等工具时，若 MCP 服务返回
    ``isError`` 或 ``error`` 字段，则抛出此异常，交由上层 Session 触发回滚。
    """

    def __init__(self, message: str, tool: Optional[str] = None,
                 code: Any = None, data: Any = None):
        super().__init__(message)
        self.tool = tool
        self.code = code
        self.data = data


__all__ = ["MCPError", "MCPConnectionError", "MCPToolError"]
