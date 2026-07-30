"""cad.adapter.mock_adapter · Mock CAD 后端（Phase 12.1）。

说明：
- 这是**确定性 Mock 后端**，不依赖任何真实 CAD 软件。
- DWG 文件以结构化 JSON 内容写入 ``*.dwg``（Mock DWG 容器格式），
  可完整回读，从而支撑 Phase 12.5 的 DWG Round-Trip 验证。
- 真实 AutoCAD 后端在 ``autocad_adapter.py`` 中通过 MCP 客户端实现（接口预留）。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (CADAdapter, CADAdapterError, DocumentNotOpenError,
                   UnsupportedOperationError)

_MOCK_DWG_MAGIC = "MOCK-DWG-1.0"


class MockCADAdapter(CADAdapter):
    """内存态 Mock CAD 后端；save_dwg/load_dwg 使用 Mock DWG 容器格式。"""

    backend_name = "mock"

    def __init__(self) -> None:
        self._doc: Optional[Dict[str, Any]] = None
        self._entity_seq = 0

    # ---- 文档生命周期 -------------------------------------------------
    def create_document(self, name: str = "drawing",
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        doc_id = f"MOCKDOC-{name}"
        self._doc = {
            "document_id": doc_id,
            "name": name,
            "metadata": dict(metadata or {}),
            "layers": [],
            "entities": [],
            "dimensions": [],
            "created_at": datetime.now().astimezone().isoformat(),
        }
        self._entity_seq = 0
        return doc_id

    def close(self) -> None:
        self._doc = None

    # ---- 内部 ----------------------------------------------------------
    def _require_doc(self) -> Dict[str, Any]:
        if self._doc is None:
            raise DocumentNotOpenError("Mock 后端：请先 create_document()")
        return self._doc

    def _next_id(self, prefix: str) -> str:
        self._entity_seq += 1
        return f"{prefix}-{self._entity_seq:05d}"

    # ---- 绘制 ---------------------------------------------------------
    def create_layer(self, name: str, color: str = "white",
                     linetype: str = "CONTINUOUS") -> Dict[str, Any]:
        doc = self._require_doc()
        layer = {"name": name, "color": color, "linetype": linetype}
        if not any(l["name"] == name for l in doc["layers"]):
            doc["layers"].append(layer)
        return layer

    def create_entity(self, entity: Dict[str, Any]) -> str:
        doc = self._require_doc()
        etype = str(entity.get("type", "")).lower()
        if not etype:
            raise CADAdapterError("entity 缺少 type 字段")
        if not self.supports(etype):
            raise UnsupportedOperationError(
                f"mock 后端不支持实体类型：{etype}")
        eid = self._next_id("E")
        record = dict(entity)
        record["id"] = eid
        record.setdefault("layer", "0")
        doc["entities"].append(record)
        return eid

    def create_dimension(self, dimension: Dict[str, Any]) -> str:
        doc = self._require_doc()
        if not self.supports("dimension"):
            raise UnsupportedOperationError("mock 后端不支持 dimension")
        did = self._next_id("DIM")
        record = dict(dimension)
        record["id"] = did
        record.setdefault("type", "linear")
        record.setdefault("layer", "DIM")
        doc["dimensions"].append(record)
        return did

    # ---- DWG I/O -------------------------------------------------------
    def save_dwg(self, path: str) -> Dict[str, Any]:
        doc = self._require_doc()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": _MOCK_DWG_MAGIC,
            "backend": self.backend_name,
            "saved_at": datetime.now().astimezone().isoformat(),
            "document": doc,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return {
            "path": str(out),
            "format": _MOCK_DWG_MAGIC,
            "layer_count": len(doc["layers"]),
            "entity_count": len(doc["entities"]),
            "dimension_count": len(doc["dimensions"]),
        }

    def load_dwg(self, path: str) -> Dict[str, Any]:
        src = Path(path)
        if not src.exists():
            raise CADAdapterError(f"DWG 文件不存在：{path}")
        try:
            payload = json.loads(src.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CADAdapterError(f"无法解析 Mock DWG：{e}")
        if payload.get("format") != _MOCK_DWG_MAGIC:
            raise CADAdapterError(
                f"非 Mock DWG 容器格式：{payload.get('format')}")
        doc = payload.get("document", {})
        return {
            "path": str(src),
            "backend": payload.get("backend", "mock"),
            "name": doc.get("name", ""),
            "metadata": doc.get("metadata", {}),
            "layers": list(doc.get("layers", [])),
            "entities": list(doc.get("entities", [])),
            "dimensions": list(doc.get("dimensions", [])),
        }

    # ---- 便捷查询（测试用） ---------------------------------------------
    @property
    def entities(self) -> List[Dict[str, Any]]:
        return list(self._require_doc()["entities"])

    @property
    def dimensions(self) -> List[Dict[str, Any]]:
        return list(self._require_doc()["dimensions"])


__all__ = ["MockCADAdapter"]
