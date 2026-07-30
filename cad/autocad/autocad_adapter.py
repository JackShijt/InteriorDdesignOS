"""AutoCADAdapter（Phase 7）— 经 MCP 接入真实 AutoCAD 后端。

实现 CADAdapter 的全部抽象方法，所有绘制调用通过 ``MCPClient`` 转译为
AutoCAD MCP 服务暴露的 ``cad.*`` 工具。**不直接生成 DWG、不调用 AutoCAD
原生 API**；CAD Framework（cad/）不知道本类存在，仅通过 ``CAD_BACKENDS``
插件注册被加载（见 cad/__init__.py）。

依赖方向（唯一允许的访问链）：
    AutoCADAdapter → CADAdapter（抽象接口）
                    → MCPClient → AutoCAD MCP → AutoCAD
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..base.cad_adapter import CADAdapter
from ..base.cad_document import CADDocument
from ..mcp.mcp_client import MCPClient
from ..mcp.mcp_exception import MCPConnectionError, MCPError
from ..mcp.mcp_protocol import (TOOL_CLOSE_DOCUMENT, TOOL_CREATE_DIMENSION,
                                TOOL_CREATE_LAYER, TOOL_CREATE_TEXT,
                                TOOL_DRAW_ARC, TOOL_DRAW_CIRCLE,
                                TOOL_DRAW_LINE, TOOL_DRAW_POLYLINE,
                                TOOL_EXPORT, TOOL_INSERT_BLOCK,
                                TOOL_OPEN_DOCUMENT, TOOL_SAVE_DOCUMENT)

Point = Union[List[float], Tuple[float, float], Tuple[float, float, float]]


class AutoCADAdapter(CADAdapter):
    """真实 AutoCAD 后端适配器（Phase 7）。

    所有几何 / 标注操作委托给注入的 ``MCPClient``（默认按 host/port 构造
    HTTP 传输）。可注入 ``client`` 以进行测试（FakeMCPClient）。
    """

    backend_name = "autocad"

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
                 timeout: float = 30, client: Optional[MCPClient] = None,
                 config: Optional[Dict[str, Any]] = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.config = config or {}
        self._client = client or MCPClient(host=host, port=port, timeout=timeout)
        self.connected = False
        self.document: Optional[CADDocument] = None
        # 执行历史（与 MockAdapter 保持同构，便于统一导出 / 调试）
        self.execution_log: List[Dict[str, Any]] = []

    # ---- 连接生命周期 ----
    def connect(self) -> None:
        self._client.connect()
        self.connected = True

    def disconnect(self) -> None:
        try:
            self._client.disconnect()
        finally:
            self.connected = False

    def open_document(self, name: str) -> CADDocument:
        resp = self._client.call_tool(TOOL_OPEN_DOCUMENT, {"name": name})
        self.document = CADDocument(name, self)
        self.execution_log.append(
            {"op": "open_document", "name": name, "result": resp})
        return self.document

    def close(self) -> Dict[str, Any]:
        resp = self._client.call_tool(TOOL_CLOSE_DOCUMENT, {})
        if self.document is not None:
            self.document.is_open = False
        rec = {"op": "close", "result": resp}
        self.execution_log.append(rec)
        return rec

    def save(self, name: Optional[str] = None) -> Dict[str, Any]:
        resp = self._client.call_tool(TOOL_SAVE_DOCUMENT, {"name": name})
        rec = {"op": "save", "name": name, "result": resp}
        self.execution_log.append(rec)
        return rec

    # ---- 图层 ----
    def create_layer(self, name: str, color: int = 7,
                     line_type: str = "Continuous") -> Dict[str, Any]:
        return self._tool(TOOL_CREATE_LAYER,
                          {"name": name, "color": color, "line_type": line_type},
                          op="create_layer")

    # ---- 几何 ----
    def draw_line(self, start: Point, end: Point,
                  layer: Optional[str] = None) -> Dict[str, Any]:
        return self._tool(TOOL_DRAW_LINE,
                          {"start": list(start), "end": list(end), "layer": layer},
                          op="draw_line")

    def draw_polyline(self, points: List[Point], layer: Optional[str] = None,
                      width: Optional[float] = None,
                      closed: bool = False) -> Dict[str, Any]:
        return self._tool(TOOL_DRAW_POLYLINE,
                          {"points": [list(p) for p in points], "layer": layer,
                           "width": width, "closed": closed},
                          op="draw_polyline")

    def draw_arc(self, center: Point, radius: float, start_angle: float,
                 end_angle: float, layer: Optional[str] = None) -> Dict[str, Any]:
        return self._tool(TOOL_DRAW_ARC,
                          {"center": list(center), "radius": radius,
                           "start_angle": start_angle, "end_angle": end_angle,
                           "layer": layer},
                          op="draw_arc")

    def draw_circle(self, center: Point, radius: float,
                    layer: Optional[str] = None) -> Dict[str, Any]:
        return self._tool(TOOL_DRAW_CIRCLE,
                          {"center": list(center), "radius": radius,
                           "layer": layer},
                          op="draw_circle")

    # ---- 标注 / 块 / 文本 ----
    def insert_block(self, name: str, position: Point,
                     layer: Optional[str] = None, scale: float = 1.0,
                     rotation: float = 0.0) -> Dict[str, Any]:
        return self._tool(TOOL_INSERT_BLOCK,
                          {"name": name, "position": list(position),
                           "layer": layer, "scale": scale, "rotation": rotation},
                          op="insert_block")

    def create_text(self, content: str, position: Point,
                    height: float = 100.0, layer: Optional[str] = None,
                    rotation: float = 0.0) -> Dict[str, Any]:
        return self._tool(TOOL_CREATE_TEXT,
                          {"content": content, "position": list(position),
                           "height": height, "layer": layer, "rotation": rotation},
                          op="create_text")

    def create_dimension(self, start: Point, end: Point,
                         layer: Optional[str] = None,
                         dim_style: str = "Standard",
                         text_override: Optional[str] = None) -> Dict[str, Any]:
        return self._tool(TOOL_CREATE_DIMENSION,
                          {"start": list(start), "end": list(end),
                           "layer": layer, "dim_style": dim_style,
                           "text_override": text_override},
                          op="create_dimension")

    # ---- 导出（仅请求 AutoCAD MCP 导出，绝不直接写 DWG）----
    def export(self, path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        resp = self._client.call_tool(
            TOOL_EXPORT, {"path": str(path) if path else None})
        rec = {"op": "export", "path": str(path) if path else None,
               "backend": "autocad", "result": resp}
        self.execution_log.append(rec)
        return rec

    # ---- 内部：统一的「工具调用 → 记录」封装 ----
    def _tool(self, tool: str, args: Dict[str, Any], op: str) -> Dict[str, Any]:
        """调用某个 CAD 工具；成功则记录到执行历史并挂到当前文档图元。

        任何 MCPError 直接向上抛出，交由 CADSession.run 触发事务回滚。
        """
        try:
            result = self._client.call_tool(tool, args)
        except MCPError:
            raise
        rec = {"op": op, **{k: v for k, v in args.items() if k != "result"},
               "result": result}
        self.execution_log.append(rec)
        if self.document is not None:
            self.document.add_entity(rec)
        return rec

    # ---- 上下文管理器（与抽象基类约定一致）----
    def __enter__(self) -> "AutoCADAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()


__all__ = ["AutoCADAdapter"]
