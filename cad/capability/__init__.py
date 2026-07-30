"""cad.capability · 后端能力系统（Phase 12.2）。"""
from .capability import (get_backend_capabilities, get_capability_registry,
                         has_capability, missing_capabilities,
                         register_backend_capabilities, select_backend)

__all__ = [
    "get_capability_registry",
    "register_backend_capabilities",
    "get_backend_capabilities",
    "has_capability",
    "missing_capabilities",
    "select_backend",
]
