"""MCP 协议定义（Phase 7 §1）。

集中定义 MCP（Model Context Protocol）方法名、AutoCAD MCP 服务暴露的工具名、
以及 JSON-RPC 风格的消息信封构造 / 解析。

职责边界（关键约束）：
- 本文件只描述「协议」：把 CADAdapter 的一次调用翻译成
  ``(工具名, 参数)``，**不写死任何 AutoCAD 原生 API**。
- AutoCADAdapter 依赖本文件做翻译；MCPClient 依赖本文件做信封。
- 不知道 CAD 业务细节，也不依赖 Agent / Runtime。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# ---- JSON-RPC / MCP 方法 ----
MCP_METHOD_INITIALIZE = "initialize"
MCP_METHOD_PING = "ping"
MCP_METHOD_TOOLS_LIST = "tools/list"
MCP_METHOD_TOOLS_CALL = "tools/call"

# ---- AutoCAD MCP 服务暴露的工具名（本系统自定义的协议层）----
# 注意：这些是「我们的 MCP 工具名」，不是 AutoCAD 内部命令；
# 真正的 AutoCAD 调用由 MCP 服务端翻译，本层不感知。
TOOL_OPEN_DOCUMENT = "cad.open_document"
TOOL_SAVE_DOCUMENT = "cad.save_document"
TOOL_CLOSE_DOCUMENT = "cad.close_document"
TOOL_CREATE_LAYER = "cad.create_layer"
TOOL_DRAW_LINE = "cad.draw_line"
TOOL_DRAW_POLYLINE = "cad.draw_polyline"
TOOL_DRAW_ARC = "cad.draw_arc"
TOOL_DRAW_CIRCLE = "cad.draw_circle"
TOOL_INSERT_BLOCK = "cad.insert_block"
TOOL_CREATE_TEXT = "cad.create_text"
TOOL_CREATE_DIMENSION = "cad.create_dimension"
TOOL_EXPORT = "cad.export"
TOOL_SEND_COMMAND = "cad.send_command"
TOOL_QUERY_STATE = "cad.query_state"


def make_request(req_id: int, method: str,
                 params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造 JSON-RPC 请求信封。"""
    req: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        req["params"] = params
    return req


def make_tool_call(req_id: int, name: str,
                   arguments: Dict[str, Any]) -> Dict[str, Any]:
    """构造 ``tools/call`` 请求信封。"""
    return make_request(req_id, MCP_METHOD_TOOLS_CALL,
                        {"name": name, "arguments": arguments})


def parse_response(payload: Any) -> Any:
    """从 MCP ``tools/call`` 响应中提取业务结果。

    标准返回形如 ``{result: {content:[{type,text}], isError:bool}}``；
    若含 ``error`` 或 ``isError`` 则抛 ``MCPToolError``。
    """
    if not isinstance(payload, dict):
        raise MCPToolError(f"非法 MCP 响应：{payload!r}")
    if "error" in payload:
        err = payload["error"] if isinstance(payload["error"], dict) else {}
        raise MCPToolError(str(err.get("message", err)),
                           code=err.get("code"), data=err.get("data"))
    result = payload.get("result", payload)
    if isinstance(result, dict) and result.get("isError"):
        content = result.get("content") or []
        msg = content[0].get("text") if content else "MCP 工具执行失败"
        raise MCPToolError(msg, data=result)
    return result


__all__ = [
    "MCP_METHOD_INITIALIZE", "MCP_METHOD_PING", "MCP_METHOD_TOOLS_LIST",
    "MCP_METHOD_TOOLS_CALL",
    "TOOL_OPEN_DOCUMENT", "TOOL_SAVE_DOCUMENT", "TOOL_CLOSE_DOCUMENT",
    "TOOL_CREATE_LAYER", "TOOL_DRAW_LINE", "TOOL_DRAW_POLYLINE",
    "TOOL_DRAW_ARC", "TOOL_DRAW_CIRCLE", "TOOL_INSERT_BLOCK",
    "TOOL_CREATE_TEXT", "TOOL_CREATE_DIMENSION", "TOOL_EXPORT",
    "TOOL_SEND_COMMAND", "TOOL_QUERY_STATE",
    "make_request", "make_tool_call", "parse_response",
]
