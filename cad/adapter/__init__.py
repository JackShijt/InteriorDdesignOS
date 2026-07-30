"""cad.adapter · 统一 CAD 后端适配器层（Phase 12.1）。

上层（Pipeline / Agent）只允许通过本包访问 CAD 后端：
    from cad.adapter import resolve_adapter
    ctx = resolve_adapter(preferred="autocad")
    adapter = ctx["adapter"]   # CADAdapter 统一接口
"""
from .autocad_adapter import AutoCADAdapter
from .base import (CADAdapter, CADAdapterError, DocumentNotOpenError,
                   UnsupportedOperationError)
from .mock_adapter import MockCADAdapter
from .registry import (available_backends, create_adapter, register_adapter,
                       resolve_adapter)

__all__ = [
    "CADAdapter",
    "CADAdapterError",
    "DocumentNotOpenError",
    "UnsupportedOperationError",
    "MockCADAdapter",
    "AutoCADAdapter",
    "register_adapter",
    "available_backends",
    "create_adapter",
    "resolve_adapter",
]
