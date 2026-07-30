"""cad.adapter.base · 统一 CAD 后端适配器接口（Phase 12.1）。

设计原则：
- 所有 CAD 后端（Mock / AutoCAD / 未来的其它软件）必须实现 ``CADAdapter``。
- 上层（Pipeline / DrawingAgent）只依赖本接口，**禁止**直接调用任何 CAD API。
- Pipeline 不知道具体 CAD 软件 —— 通过 ``cad.adapter.registry`` 按名称/能力获取。

接口契约（Phase 12 规范）：
    create_document() / create_layer() / create_entity() /
    create_dimension() / save_dwg() / load_dwg() / close()

数据约定（后端无关的中性结构，不属于 Schema Contract）：
- entity: {"type": "line|polyline|circle|arc|text|block", "layer": str, ...几何字段}
- dimension: {"type": "linear|aligned|angular", "start": {x,y}, "end": {x,y},
              "value": float, "layer": str}
- load_dwg 返回 DWGDocumentData：{"path", "layers": [...], "entities": [...],
              "dimensions": [...], "metadata": {...}}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CADAdapterError(Exception):
    """CAD 适配器统一异常基类。"""


class DocumentNotOpenError(CADAdapterError):
    """在未创建/未打开文档时执行绘制操作。"""


class UnsupportedOperationError(CADAdapterError):
    """后端不支持所请求的能力（配合 capability 系统做降级）。"""


class CADAdapter(ABC):
    """统一 CAD 后端接口。

    生命周期：
        create_document() -> create_layer()/create_entity()/create_dimension()*
        -> save_dwg(path) -> close()
    回读：
        load_dwg(path) -> DWGDocumentData（供 GeneratedModel / Round-Trip 验证）
    """

    #: 后端标识（子类必须覆盖，如 "mock" / "autocad"）
    backend_name: str = "abstract"

    # ---- 文档生命周期 -------------------------------------------------
    @abstractmethod
    def create_document(self, name: str = "drawing",
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """新建文档，返回 document_id。"""

    @abstractmethod
    def close(self) -> None:
        """关闭当前文档并释放资源（幂等）。"""

    # ---- 绘制 ---------------------------------------------------------
    @abstractmethod
    def create_layer(self, name: str, color: str = "white",
                     linetype: str = "CONTINUOUS") -> Dict[str, Any]:
        """创建图层，返回图层描述 dict。"""

    @abstractmethod
    def create_entity(self, entity: Dict[str, Any]) -> str:
        """创建一个几何实体（line/polyline/circle/arc/text/block…），返回 entity_id。"""

    @abstractmethod
    def create_dimension(self, dimension: Dict[str, Any]) -> str:
        """创建一个标注实体，返回 dimension_id。"""

    # ---- DWG I/O -------------------------------------------------------
    @abstractmethod
    def save_dwg(self, path: str) -> Dict[str, Any]:
        """将当前文档保存为 DWG 文件，返回 {"path", "entity_count", ...}。"""

    @abstractmethod
    def load_dwg(self, path: str) -> Dict[str, Any]:
        """读取 DWG 文件，返回 DWGDocumentData（layers/entities/dimensions）。"""

    # ---- 通用查询（默认实现，可覆盖） -----------------------------------
    def capabilities(self) -> List[str]:
        """返回后端能力列表（默认从 capability 注册表读取）。"""
        from cad.capability import get_backend_capabilities
        return get_backend_capabilities(self.backend_name)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities()


__all__ = [
    "CADAdapter",
    "CADAdapterError",
    "DocumentNotOpenError",
    "UnsupportedOperationError",
]
