"""cad.capability · 后端能力系统（Phase 12.2）。

用途：
- 能力检测：``has_capability(backend, cap)``
- 后端切换：``select_backend(required_caps, preferred)``
- 降级处理：首选后端能力不足时自动降级到满足能力的后端（默认 mock）

能力定义存放于同目录 ``backends.json``：
    {"backend": "autocad", "capabilities": ["line", "polyline", ...]}

本模块只描述能力，不接触任何 CAD API。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_CAPABILITY_FILE = Path(__file__).parent / "backends.json"

# 运行期注册（测试/扩展后端时可动态补充，不必改 JSON）
_runtime_registry: Dict[str, List[str]] = {}


def _load_file_registry() -> Dict[str, List[str]]:
    if not _CAPABILITY_FILE.exists():
        return {}
    data = json.loads(_CAPABILITY_FILE.read_text(encoding="utf-8"))
    return {
        str(item["backend"]): list(item.get("capabilities", []))
        for item in data.get("backends", [])
    }


def get_capability_registry() -> Dict[str, List[str]]:
    """合并 JSON 定义与运行期注册，返回 {backend: [capability...]}。"""
    registry = _load_file_registry()
    registry.update({k: list(v) for k, v in _runtime_registry.items()})
    return registry


def register_backend_capabilities(backend: str,
                                  capabilities: Sequence[str]) -> None:
    """运行期注册/覆盖一个后端的能力集合。"""
    _runtime_registry[backend] = list(capabilities)


def get_backend_capabilities(backend: str) -> List[str]:
    return get_capability_registry().get(backend, [])


def has_capability(backend: str, capability: str) -> bool:
    return capability in get_backend_capabilities(backend)


def missing_capabilities(backend: str,
                         required: Sequence[str]) -> List[str]:
    caps = set(get_backend_capabilities(backend))
    return [c for c in required if c not in caps]


def select_backend(required: Sequence[str],
                   preferred: Optional[str] = None,
                   fallback: str = "mock") -> Dict[str, Any]:
    """按能力选择后端（含降级处理）。

    返回：{"backend": str, "degraded": bool, "reason": str}
    - preferred 满足全部 required → 直接使用
    - 否则在注册表中找第一个满足的后端（fallback 优先）
    - 全部不满足 → 抛 ValueError
    """
    registry = get_capability_registry()

    def _ok(name: str) -> bool:
        return name in registry and not missing_capabilities(name, required)

    if preferred and _ok(preferred):
        return {"backend": preferred, "degraded": False, "reason": "preferred"}

    candidates = [fallback] + [b for b in registry if b != fallback]
    for name in candidates:
        if _ok(name):
            reason = (f"degraded from {preferred!r}: missing "
                      f"{missing_capabilities(preferred, required)}"
                      if preferred else "no preferred backend")
            return {"backend": name, "degraded": bool(preferred), "reason": reason}

    raise ValueError(f"没有后端满足能力要求：{list(required)}")


__all__ = [
    "get_capability_registry",
    "register_backend_capabilities",
    "get_backend_capabilities",
    "has_capability",
    "missing_capabilities",
    "select_backend",
]
