"""cad（Phase 6 + Phase 7）— CAD 抽象层与后端插件系统。

依赖约束（Phase 6 §禁止 / Phase 7 §禁止）：
- cad/ 不得 import runtime / orchestrator / agents / professional（最底层之一）。
- 具体后端（autocad / mock）通过 ``CAD_BACKENDS`` 注册表被 ``build_cad_backend``
  按名加载，CAD Framework 不感知任何具体后端。

后端加载（Phase 7 §3）：
- build_cad_backend(name=None, config=None, **kwargs)
  - name 缺省时从 config["cad"]["backend"] 取，再兜底 "mock"
  - name == "autocad"：从 config["autocad"] 注入 host/port/timeout（禁止代码内写死）
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .base.cad_adapter import CADAdapter, CAD_ADAPTER_METHODS
from .base.cad_document import CADDocument
from .base.cad_transaction import CADTransaction, CADTransactionError, TransactionState
from .base.cad_session import CADSession
from .command import (COMMAND_REGISTRY, CreateLayerCommand, CreateTextCommand,
                       DimensionCommand, DoorCommand, DrawArcCommand,
                       DrawCircleCommand, DrawLineCommand, DrawPolylineCommand,
                       DrawingCommand, DrawingCommandQueue, FurnitureCommand,
                       InsertBlockCommand, WallCommand, WindowCommand)
from .mock.mock_adapter import MockAdapter
from .mock.mock_document import MockDocument
from .autocad.autocad_adapter import AutoCADAdapter
from .validator import CADValidator, CADValidationError
from .mcp.mcp_client import (HTTPMCPTransport, MCPClient, MCPTransport)
from .mcp.mcp_exception import (MCPConnectionError, MCPError, MCPToolError)
from .mcp.mcp_protocol import (TOOL_CLOSE_DOCUMENT, TOOL_CREATE_DIMENSION,
                               TOOL_CREATE_LAYER, TOOL_CREATE_TEXT,
                               TOOL_DRAW_ARC, TOOL_DRAW_CIRCLE, TOOL_DRAW_LINE,
                               TOOL_DRAW_POLYLINE, TOOL_EXPORT,
                               TOOL_INSERT_BLOCK, TOOL_OPEN_DOCUMENT,
                               TOOL_SAVE_DOCUMENT, TOOL_SEND_COMMAND,
                               TOOL_QUERY_STATE, make_request, make_tool_call,
                               parse_response)

# ---- 后端插件注册表（Phase 6 §七 / Phase 7 §三）----
CAD_BACKENDS: Dict[str, Callable[..., CADAdapter]] = {
    "mock": MockAdapter,
    "autocad": AutoCADAdapter,
}


def build_cad_backend(name: Optional[str] = None,
                      config: Optional[Dict[str, Any]] = None,
                      output_dir: Optional[Any] = None,
                      **kwargs: Any) -> CADAdapter:
    """按名构造一个 CAD 后端适配器（插件机制）。

    Args:
        name: 后端名；缺省时依次取 config["cad"]["backend"] / "mock"。
        config: 运行时配置 dict（来自 config/runtime.yaml），
            用于向 autocad 后端注入 host/port/timeout，避免代码写死。
        output_dir: 仅 MockAdapter 使用（落盘 drawing_command_log.json）。
            不传给 AutoCADAdapter（其导出路径由 export(path=...) / 配置决定）。
        **kwargs: 透传给后端构造器的其余参数。
    """
    if config and "cad" in config:
        name = name or config["cad"].get("backend", "mock")
    if name is None:
        name = "mock"
    if name not in CAD_BACKENDS:
        raise ValueError(
            f"未知 CAD 后端：{name!r}（可用：{sorted(CAD_BACKENDS)}）")

    if name == "mock":
        kwargs.setdefault("output_dir", output_dir)
    elif name == "autocad":
        ac = (config or {}).get("autocad", {}) if config else {}
        kwargs.setdefault("host", ac.get("host"))
        kwargs.setdefault("port", ac.get("port"))
        kwargs.setdefault("timeout", ac.get("timeout"))
        kwargs.setdefault("config", config or {})

    return CAD_BACKENDS[name](**kwargs)


__all__ = [
    "CADAdapter", "CAD_ADAPTER_METHODS", "CADDocument",
    "CADTransaction", "CADTransactionError", "TransactionState",
    "CADSession",
    "COMMAND_REGISTRY", "CreateLayerCommand", "CreateTextCommand",
    "DimensionCommand", "DoorCommand", "DrawArcCommand", "DrawCircleCommand",
    "DrawLineCommand", "DrawPolylineCommand", "DrawingCommand",
    "DrawingCommandQueue", "FurnitureCommand", "InsertBlockCommand",
    "WallCommand", "WindowCommand",
    "MockAdapter", "MockDocument", "AutoCADAdapter",
    "CADValidator", "CADValidationError",
    "HTTPMCPTransport", "MCPClient", "MCPTransport",
    "MCPError", "MCPConnectionError", "MCPToolError",
    "TOOL_CLOSE_DOCUMENT", "TOOL_CREATE_DIMENSION", "TOOL_CREATE_LAYER",
    "TOOL_CREATE_TEXT", "TOOL_DRAW_ARC", "TOOL_DRAW_CIRCLE", "TOOL_DRAW_LINE",
    "TOOL_DRAW_POLYLINE", "TOOL_EXPORT", "TOOL_INSERT_BLOCK",
    "TOOL_OPEN_DOCUMENT", "TOOL_SAVE_DOCUMENT", "TOOL_SEND_COMMAND",
    "TOOL_QUERY_STATE", "make_request", "make_tool_call", "parse_response",
    "CAD_BACKENDS", "build_cad_backend",
]
