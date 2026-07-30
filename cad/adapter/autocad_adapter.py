"""cad.adapter.autocad_adapter · AutoCAD 后端适配器（Phase 12.1 / 12.3）。

说明：
- 通过 ``AutoCADMCPClient`` 与 AutoCAD MCP 服务通信；本阶段**不要求真实连接**。
- 未注入可用 transport 时，create_document() 会抛 CADAdapterError，
  由 ``cad.adapter.registry`` / capability 系统降级到 mock 后端。
- 严禁在此之外的任何 Agent / Pipeline 代码直接调用 CAD API。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from cad.mcp.autocad_mcp_client import AutoCADMCPClient
from cad.mcp.mcp_exception import MCPError

from .base import CADAdapter, CADAdapterError, DocumentNotOpenError


class AutoCADAdapter(CADAdapter):
    """AutoCAD 后端：把统一接口翻译为 MCP 工具调用。"""

    backend_name = "autocad"

    def __init__(self, client: Optional[AutoCADMCPClient] = None,
                 host: Optional[str] = None, port: Optional[int] = None):
        self._client = client or AutoCADMCPClient(host=host, port=port)
        self._doc_id: Optional[str] = None

    # ---- 文档生命周期 ---------------------------------------------------
    def create_document(self, name: str = "drawing",
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        try:
            if not self._client.connected:
                self._client.connect()
            result = self._client.execute(
                "cad.create_document", {"name": name,
                                        "metadata": metadata or {}})
        except MCPError as e:
            raise CADAdapterError(f"AutoCAD 后端不可用：{e}")
        self._doc_id = (result or {}).get("document_id", f"ACADDOC-{name}") \
            if isinstance(result, dict) else f"ACADDOC-{name}"
        return self._doc_id

    def close(self) -> None:
        try:
            if self._client.connected:
                self._client.execute("cad.close_document", {})
                self._client.disconnect()
        except MCPError:
            pass
        finally:
            self._doc_id = None

    # ---- 内部 -----------------------------------------------------------
    def _require_doc(self) -> str:
        if self._doc_id is None:
            raise DocumentNotOpenError("AutoCAD 后端：请先 create_document()")
        return self._doc_id

    def _call(self, tool: str, args: Dict[str, Any]) -> Any:
        try:
            return self._client.execute(tool, args)
        except MCPError as e:
            raise CADAdapterError(f"AutoCAD MCP 调用失败（{tool}）：{e}")

    # ---- 绘制 -----------------------------------------------------------
    def create_layer(self, name: str, color: str = "white",
                     linetype: str = "CONTINUOUS") -> Dict[str, Any]:
        self._require_doc()
        self._call("cad.create_layer",
                   {"name": name, "color": color, "linetype": linetype})
        return {"name": name, "color": color, "linetype": linetype}

    def create_entity(self, entity: Dict[str, Any]) -> str:
        self._require_doc()
        result = self._call("cad.create_entity", dict(entity))
        if isinstance(result, dict) and "id" in result:
            return str(result["id"])
        return "ACAD-ENTITY"

    def create_dimension(self, dimension: Dict[str, Any]) -> str:
        self._require_doc()
        result = self._call("cad.create_dimension", dict(dimension))
        if isinstance(result, dict) and "id" in result:
            return str(result["id"])
        return "ACAD-DIM"

    # ---- DWG I/O ---------------------------------------------------------
    def save_dwg(self, path: str) -> Dict[str, Any]:
        self._require_doc()
        result = self._call("cad.save_dwg", {"path": path})
        return result if isinstance(result, dict) else {"path": path}

    def load_dwg(self, path: str) -> Dict[str, Any]:
        result = self._call("cad.load_dwg", {"path": path})
        if not isinstance(result, dict):
            raise CADAdapterError("AutoCAD load_dwg 返回格式异常")
        result.setdefault("path", path)
        result.setdefault("layers", [])
        result.setdefault("entities", [])
        result.setdefault("dimensions", [])
        return result


__all__ = ["AutoCADAdapter"]
