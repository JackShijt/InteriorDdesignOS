"""cad.adapter.registry · CAD 后端适配器注册表（Phase 12.1 / 12.2）。

职责：
- 按名称注册/创建适配器（禁止上层硬编码具体后端类）。
- 结合 capability 系统做能力检测与**降级处理**：
  首选后端能力不足或不可用时，自动降级到 mock。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from cad.capability import missing_capabilities, select_backend

from .autocad_adapter import AutoCADAdapter
from .base import CADAdapter, CADAdapterError
from .mock_adapter import MockCADAdapter

_FACTORIES: Dict[str, Callable[..., CADAdapter]] = {
    "mock": MockCADAdapter,
    "autocad": AutoCADAdapter,
}


def register_adapter(name: str, factory: Callable[..., CADAdapter]) -> None:
    """注册自定义后端适配器工厂。"""
    _FACTORIES[name] = factory


def available_backends() -> List[str]:
    return sorted(_FACTORIES)


def create_adapter(name: str, **kwargs: Any) -> CADAdapter:
    """按名称创建适配器实例。"""
    if name not in _FACTORIES:
        raise CADAdapterError(
            f"未注册的 CAD 后端：{name}（可用：{available_backends()}）")
    return _FACTORIES[name](**kwargs)


def resolve_adapter(preferred: Optional[str] = None,
                    required: Sequence[str] = ("line", "polyline", "layer",
                                               "dimension", "save_dwg",
                                               "read_dwg"),
                    probe: bool = True,
                    **kwargs: Any) -> Dict[str, Any]:
    """能力检测 + 后端选择 + 降级处理（Phase 12.2）。

    步骤：
    1. capability 层按 required 选出满足能力的后端（select_backend）。
    2. probe=True 时对所选后端做可用性探测（create_document/close）；
       探测失败（如 AutoCAD MCP 未连接）→ 降级到 mock。

    返回：{"adapter": CADAdapter, "backend": str, "degraded": bool, "reason": str}
    """
    choice = select_backend(required, preferred=preferred, fallback="mock")
    backend = choice["backend"]
    degraded = bool(choice["degraded"])
    reason = str(choice["reason"])

    adapter = create_adapter(backend, **kwargs)
    if probe and backend != "mock":
        try:
            adapter.create_document("__probe__")
            adapter.close()
        except CADAdapterError as e:
            # 后端不可用 → 降级到 mock
            missing = missing_capabilities("mock", required)
            if missing:
                raise CADAdapterError(
                    f"后端 {backend} 不可用且 mock 缺少能力 {missing}") from e
            adapter = create_adapter("mock")
            degraded = True
            reason = f"backend {backend!r} unavailable: {e}"
            backend = "mock"

    return {"adapter": adapter, "backend": backend,
            "degraded": degraded, "reason": reason}


__all__ = [
    "register_adapter",
    "available_backends",
    "create_adapter",
    "resolve_adapter",
]
