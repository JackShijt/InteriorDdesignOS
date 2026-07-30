"""cad/mcp（Phase 7 §1）— MCP Client Layer。

封装与 AutoCAD MCP 服务的通信；不知道 CAD 业务、不依赖 Agent / Runtime。
"""
from __future__ import annotations

from .mcp_exception import MCPConnectionError, MCPError, MCPToolError
from .mcp_protocol import (MCP_METHOD_INITIALIZE, MCP_METHOD_PING,
                           MCP_METHOD_TOOLS_LIST, MCP_METHOD_TOOLS_CALL,
                           TOOL_OPEN_DOCUMENT, TOOL_SAVE_DOCUMENT,
                           TOOL_CLOSE_DOCUMENT, TOOL_CREATE_LAYER,
                           TOOL_DRAW_LINE, TOOL_DRAW_POLYLINE, TOOL_DRAW_ARC,
                           TOOL_DRAW_CIRCLE, TOOL_INSERT_BLOCK,
                           TOOL_CREATE_TEXT, TOOL_CREATE_DIMENSION,
                           TOOL_EXPORT, TOOL_SEND_COMMAND, TOOL_QUERY_STATE,
                           make_request, make_tool_call, parse_response)
from .mcp_client import (HTTPMCPTransport, MCPClient, MCPTransport)
from .autocad_mcp_client import AutoCADMCPClient  # noqa: E402 （Phase 12.3）

__all__ = [
    "MCPTransport", "HTTPMCPTransport", "MCPClient", "AutoCADMCPClient",
    "MCPError", "MCPConnectionError", "MCPToolError",
    "MCP_METHOD_INITIALIZE", "MCP_METHOD_PING", "MCP_METHOD_TOOLS_LIST",
    "MCP_METHOD_TOOLS_CALL",
    "TOOL_OPEN_DOCUMENT", "TOOL_SAVE_DOCUMENT", "TOOL_CLOSE_DOCUMENT",
    "TOOL_CREATE_LAYER", "TOOL_DRAW_LINE", "TOOL_DRAW_POLYLINE",
    "TOOL_DRAW_ARC", "TOOL_DRAW_CIRCLE", "TOOL_INSERT_BLOCK",
    "TOOL_CREATE_TEXT", "TOOL_CREATE_DIMENSION", "TOOL_EXPORT",
    "TOOL_SEND_COMMAND", "TOOL_QUERY_STATE",
    "make_request", "make_tool_call", "parse_response",
]
